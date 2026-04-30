import random
from datetime import datetime

from fastapi import HTTPException
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.core.crud import CRUDBase
from app.exam.constants import ExamPracticeSessionStatus
from app.exam.models import ExamBank, ExamPracticeAnswer, ExamPracticeSession, ExamPracticeWrongQuestion, ExamQuestion
from app.exam.schemas.practice import ExamPracticeActionPayload, ExamPracticeAnswerPayload, ExamPracticeStartPayload
from app.exam.utils import is_objective_question, normalize_user_answer, sanitize_question_snapshot

from .question import exam_question_controller


class ExamPracticeController(CRUDBase[ExamPracticeSession, dict, dict]):
    def __init__(self):
        super().__init__(model=ExamPracticeSession)

    async def list_practice_banks(self):
        return await ExamBank.filter(is_active=True).order_by("-id").values("id", "name", "desc", "question_count")

    async def list_practice_questions(
        self,
        page: int,
        page_size: int,
        bank_id: int | None = None,
        question_type: str | None = None,
        difficulty: str | None = None,
        stem: str | None = None,
    ):
        total, data = await exam_question_controller.list_questions(
            page=page,
            page_size=page_size,
            bank_id=bank_id,
            question_type=question_type,
            difficulty=difficulty,
            stem=stem,
            selectable_only=True,
        )
        safe_fields = {
            "id",
            "bank_id",
            "bank_name",
            "question_type",
            "category_path",
            "stem",
            "tags",
            "difficulty",
            "default_score",
        }
        return total, [{key: item.get(key) for key in safe_fields} for item in data]

    async def _serialize_answer(self, answer: ExamPracticeAnswer, reveal_all: bool = False):
        item = await answer.to_dict()
        reveal_answer = reveal_all or bool(answer.answered_at)
        item["answer_snapshot"] = sanitize_question_snapshot(answer.answer_snapshot or {}, reveal_answer=reveal_answer)
        item["answer_payload"] = normalize_user_answer(answer.question_type, item.get("answer_payload"))
        item["reveal_answer"] = reveal_answer
        if item.get("answer_payload") is None:
            item["answer_payload"] = "" if item["question_type"] in {"fill_blank", "short_answer"} else []
        return item

    async def _serialize_session(self, session: ExamPracticeSession, include_answers: bool = True):
        data = await session.to_dict()
        if session.bank_id:
            bank = await ExamBank.filter(id=session.bank_id).first()
            data["bank"] = await bank.to_dict() if bank else {}
        else:
            data["bank"] = {}

        if include_answers:
            answer_objs = await ExamPracticeAnswer.filter(session_id=session.id).order_by("sort_order", "id").all()
            reveal_all = session.status == ExamPracticeSessionStatus.COMPLETED
            data["answers"] = [await self._serialize_answer(answer, reveal_all=reveal_all) for answer in answer_objs]
        return data

    async def _get_owned_session(self, session_id: int, user_id: int):
        session = await ExamPracticeSession.filter(id=session_id, user_id=user_id).first()
        if not session:
            raise HTTPException(status_code=404, detail="练习不存在")
        return session

    async def start_practice(self, obj_in: ExamPracticeStartPayload, user_id: int):
        active_bank_ids = await ExamBank.filter(is_active=True).values_list("id", flat=True)
        query = ExamQuestion.filter(is_active=True, bank_id__in=list(active_bank_ids))

        question_ids = obj_in.question_ids or []
        if question_ids:
            query = query.filter(id__in=question_ids)
        else:
            if obj_in.bank_id:
                query = query.filter(bank_id=obj_in.bank_id)
            if obj_in.question_type:
                query = query.filter(question_type=obj_in.question_type)
            if obj_in.difficulty:
                query = query.filter(difficulty=obj_in.difficulty)

        question_objs = await query.all()
        if not question_objs:
            raise HTTPException(status_code=400, detail="当前条件下没有可练习题目")

        if question_ids and len(question_objs) != len(question_ids):
            raise HTTPException(status_code=400, detail="存在不存在或不可用的练习题目")

        if question_ids:
            question_order = {question_id: index for index, question_id in enumerate(question_ids)}
            question_objs.sort(key=lambda item: question_order.get(item.id, len(question_order)))
            picked_questions = question_objs
        else:
            random.shuffle(question_objs)
            picked_questions = question_objs[: obj_in.question_count]

        async with in_transaction() as connection:
            session = await ExamPracticeSession.create(
                user_id=user_id,
                bank_id=obj_in.bank_id,
                question_type=obj_in.question_type,
                difficulty=obj_in.difficulty,
                question_count=len(picked_questions),
                using_db=connection,
            )
            for index, question in enumerate(picked_questions, start=1):
                snapshot = await exam_question_controller.build_snapshot(question)
                await ExamPracticeAnswer.create(
                    session_id=session.id,
                    question_id=question.id,
                    question_type=question.question_type,
                    answer_snapshot=snapshot,
                    sort_order=index,
                    using_db=connection,
                )

        return await self._serialize_session(session)

    async def get_session_detail(self, session_id: int, user_id: int):
        session = await self._get_owned_session(session_id, user_id)
        return await self._serialize_session(session)

    async def list_my_sessions(self, user_id: int, page: int, page_size: int):
        total, sessions = await self.list(page=page, page_size=page_size, search=Q(user_id=user_id), order=["-id"])
        data = [await self._serialize_session(session, include_answers=False) for session in sessions]
        return total, data

    async def retry_practice(self, obj_in: ExamPracticeActionPayload, user_id: int):
        session = await self._get_owned_session(obj_in.session_id, user_id)
        answers = await ExamPracticeAnswer.filter(session_id=session.id).order_by("sort_order", "id").all()
        question_ids = [answer.question_id for answer in answers]
        if not question_ids:
            raise HTTPException(status_code=400, detail="当前练习没有可重练题目")

        return await self.start_practice(
            obj_in=ExamPracticeStartPayload(
                bank_id=session.bank_id,
                question_type=session.question_type,
                difficulty=session.difficulty,
                question_count=len(question_ids),
                question_ids=question_ids,
            ),
            user_id=user_id,
        )

    async def delete_practice(self, session_id: int, user_id: int):
        session = await self._get_owned_session(session_id, user_id)
        await ExamPracticeAnswer.filter(session_id=session.id).delete()
        await session.delete()

    async def _update_wrong_question(self, user_id: int, answer: ExamPracticeAnswer, is_correct: bool | None):
        if is_correct is None:
            return

        wrong_row = await ExamPracticeWrongQuestion.filter(user_id=user_id, question_id=answer.question_id).first()
        if is_correct:
            if wrong_row:
                wrong_row.correct_count += 1
                await wrong_row.save()
            return

        if not wrong_row:
            wrong_row = await ExamPracticeWrongQuestion.create(
                user_id=user_id,
                question_id=answer.question_id,
                wrong_count=0,
                correct_count=0,
            )
        wrong_row.wrong_count += 1
        wrong_row.mastered_at = None
        wrong_row.last_wrong_at = datetime.now()
        await wrong_row.save()

    async def submit_answer(self, obj_in: ExamPracticeAnswerPayload, user_id: int):
        answer = await ExamPracticeAnswer.filter(id=obj_in.answer_id).first()
        if not answer:
            raise HTTPException(status_code=404, detail="练习题目不存在")

        session = await self._get_owned_session(answer.session_id, user_id)
        if session.status != ExamPracticeSessionStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="当前练习已结束")
        if answer.answered_at:
            return await self._serialize_session(session)

        normalized_answer = normalize_user_answer(answer.question_type, obj_in.answer_payload)
        if is_objective_question(answer.question_type):
            correct_answer = normalize_user_answer(
                answer.question_type,
                (answer.answer_snapshot or {}).get("correct_answer") or [],
            )
            is_correct = normalized_answer == correct_answer and bool(correct_answer)
            answer.answer_payload = normalized_answer
        else:
            is_correct = None
            answer.answer_payload = {"text": normalized_answer}

        answer.is_correct = is_correct
        answer.answered_at = datetime.now()
        await answer.save()

        session.answered_count += 1
        if is_correct is True:
            session.correct_count += 1
        if is_correct is False:
            session.wrong_count += 1
        if session.answered_count >= session.question_count:
            session.status = ExamPracticeSessionStatus.COMPLETED
            session.finished_at = datetime.now()
        await session.save()

        await self._update_wrong_question(user_id, answer, is_correct)
        return await self._serialize_session(session)

    async def finish_practice(self, obj_in: ExamPracticeActionPayload, user_id: int):
        session = await self._get_owned_session(obj_in.session_id, user_id)
        if session.status != ExamPracticeSessionStatus.COMPLETED:
            session.status = ExamPracticeSessionStatus.COMPLETED
            session.finished_at = datetime.now()
            await session.save()
        return await self._serialize_session(session)


exam_practice_controller = ExamPracticeController()
