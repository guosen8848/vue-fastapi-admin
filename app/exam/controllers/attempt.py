from datetime import datetime

from fastapi import HTTPException
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.core.crud import CRUDBase
from app.exam.constants import ExamAttemptStatus, ExamJudgeStatus, ExamPaperStatus
from app.exam.models import ExamAnswer, ExamAttempt, ExamPaper, ExamPaperQuestion
from app.exam.schemas.attempt import ExamAttemptSavePayload, ExamAttemptSubmitPayload
from app.exam.utils import (
    is_objective_question,
    normalize_user_answer,
    round_score,
    sanitize_question_snapshot,
    with_paper_question_snapshot,
)
from app.models.admin import User


class ExamAttemptController(CRUDBase[ExamAttempt, dict, dict]):
    def __init__(self):
        super().__init__(model=ExamAttempt)

    async def _get_paper(self, paper_id: int):
        paper = await ExamPaper.filter(id=paper_id).first()
        if not paper:
            raise HTTPException(status_code=404, detail="试卷不存在")
        return paper

    async def _get_owned_attempt(self, attempt_id: int, user_id: int):
        attempt = await ExamAttempt.filter(id=attempt_id, user_id=user_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="答卷不存在")
        return attempt

    async def _serialize_attempt(self, attempt: ExamAttempt, reveal_answer: bool):
        paper = await ExamPaper.get(id=attempt.paper_id)
        data = await attempt.to_dict()
        data["paper"] = await paper.to_dict()

        answer_objs = await ExamAnswer.filter(attempt_id=attempt.id).order_by("id").all()
        answer_rows = []
        for answer in answer_objs:
            item = await answer.to_dict()
            snapshot = answer.answer_snapshot or {}
            normalized_answer = normalize_user_answer(answer.question_type, item.get("answer_payload"))
            item["answer_snapshot"] = sanitize_question_snapshot(snapshot, reveal_answer=reveal_answer)
            item["answer_payload"] = normalized_answer
            if item.get("answer_payload") is None:
                item["answer_payload"] = "" if item["question_type"] in {"fill_blank", "short_answer"} else []
            item["sort_order"] = snapshot.get("sort_order", 0)
            answer_rows.append(item)

        answer_rows.sort(key=lambda item: (item["sort_order"], item["id"]))
        data["answers"] = answer_rows
        data["can_submit"] = attempt.status == ExamAttemptStatus.IN_PROGRESS
        data["show_result"] = reveal_answer
        return data

    async def list_answerable_papers(self, user_id: int, page: int, page_size: int, title: str | None = None):
        q = Q(status=ExamPaperStatus.PUBLISHED, is_active=True)
        if title:
            q &= Q(title__contains=title)

        query = ExamPaper.filter(q).order_by("-id")
        total = await query.count()
        paper_objs = await query.offset((page - 1) * page_size).limit(page_size)
        attempts = await ExamAttempt.filter(user_id=user_id, paper_id__in=[paper.id for paper in paper_objs]).all()
        attempt_map = {attempt.paper_id: attempt for attempt in attempts}

        data = []
        for paper in paper_objs:
            item = await paper.to_dict()
            attempt = attempt_map.get(paper.id)
            item["attempt"] = await attempt.to_dict() if attempt else None
            data.append(item)
        return total, data

    async def get_answerable_paper(self, paper_id: int, user_id: int):
        paper = await ExamPaper.filter(id=paper_id, status=ExamPaperStatus.PUBLISHED, is_active=True).first()
        if not paper:
            raise HTTPException(status_code=404, detail="试卷不存在或未发布")
        data = await paper.to_dict()
        attempt = await ExamAttempt.filter(paper_id=paper_id, user_id=user_id).first()
        data["attempt"] = await attempt.to_dict() if attempt else None
        return data

    async def start_attempt(self, paper_id: int, user_id: int):
        paper = await ExamPaper.filter(id=paper_id, status=ExamPaperStatus.PUBLISHED, is_active=True).first()
        if not paper:
            raise HTTPException(status_code=400, detail="当前试卷不可作答")

        existing_attempt = await ExamAttempt.filter(paper_id=paper_id, user_id=user_id).first()
        if existing_attempt:
            if existing_attempt.status == ExamAttemptStatus.IN_PROGRESS:
                return await self.get_my_attempt_detail(existing_attempt.id, user_id)
            raise HTTPException(status_code=400, detail="当前试卷已提交，不能再次作答")

        paper_questions = await ExamPaperQuestion.filter(paper_id=paper_id).order_by("sort_order", "id")
        if not paper_questions:
            raise HTTPException(status_code=400, detail="当前试卷没有可作答题目")

        async with in_transaction() as connection:
            attempt = await ExamAttempt.create(paper_id=paper_id, user_id=user_id, using_db=connection)
            for paper_question in paper_questions:
                snapshot = with_paper_question_snapshot(
                    paper_question.question_snapshot or {},
                    paper_question.score,
                    paper_question.sort_order,
                    paper_question_id=paper_question.id,
                )
                await ExamAnswer.create(
                    attempt_id=attempt.id,
                    paper_question_id=paper_question.id,
                    question_id=paper_question.question_id,
                    question_type=paper_question.question_snapshot["question_type"],
                    answer_snapshot=snapshot,
                    using_db=connection,
                )

        return await self.get_my_attempt_detail(attempt.id, user_id)

    async def _save_answers(self, attempt: ExamAttempt, answers: list[dict]):
        answer_objs = await ExamAnswer.filter(attempt_id=attempt.id).all()
        answer_map = {answer.paper_question_id: answer for answer in answer_objs}

        for payload in answers:
            answer = answer_map.get(payload["paper_question_id"])
            if not answer:
                raise HTTPException(status_code=400, detail="存在不属于当前试卷的题目答案")
            normalized_answer = normalize_user_answer(answer.question_type, payload.get("answer_payload"))
            answer.answer_payload = normalized_answer if is_objective_question(answer.question_type) else {"text": normalized_answer}
            await answer.save()

    async def save_attempt(self, obj_in: ExamAttemptSavePayload, user_id: int):
        attempt = await self._get_owned_attempt(obj_in.attempt_id, user_id)
        if attempt.status != ExamAttemptStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="当前答卷不允许继续保存")
        await self._save_answers(attempt, [item.model_dump() for item in obj_in.answers])
        return await self.get_my_attempt_detail(attempt.id, user_id)

    async def submit_attempt(self, obj_in: ExamAttemptSubmitPayload, user_id: int):
        attempt = await self._get_owned_attempt(obj_in.attempt_id, user_id)
        if attempt.status != ExamAttemptStatus.IN_PROGRESS:
            raise HTTPException(status_code=400, detail="当前答卷不允许提交")

        await self._save_answers(attempt, [item.model_dump() for item in obj_in.answers])
        answer_objs = await ExamAnswer.filter(attempt_id=attempt.id).all()

        objective_score = 0.0
        has_manual_questions = False
        judged_at = datetime.now()

        for answer in answer_objs:
            snapshot = answer.answer_snapshot or {}
            score = round_score(snapshot.get("score"))
            normalized_answer = normalize_user_answer(answer.question_type, answer.answer_payload)
            answer.answer_payload = normalized_answer if is_objective_question(answer.question_type) else {"text": normalized_answer}

            if is_objective_question(answer.question_type):
                correct_answer = normalize_user_answer(answer.question_type, snapshot.get("correct_answer") or [])
                is_correct = normalized_answer == correct_answer and bool(correct_answer)
                answer.is_correct = is_correct
                answer.auto_score = score if is_correct else 0
                answer.manual_score = 0
                answer.final_score = answer.auto_score
                answer.judge_status = ExamJudgeStatus.AUTO_CORRECT if is_correct else ExamJudgeStatus.AUTO_WRONG
                answer.judged_at = judged_at
                answer.judged_by = None
                objective_score += answer.auto_score
            else:
                has_manual_questions = True
                answer.is_correct = None
                answer.auto_score = 0
                answer.manual_score = 0
                answer.final_score = 0
                answer.judge_status = ExamJudgeStatus.MANUAL_PENDING
                answer.judged_at = None
                answer.judged_by = None
            await answer.save()

        attempt.objective_score = round_score(objective_score)
        attempt.subjective_score = 0
        attempt.total_score = round_score(objective_score)
        attempt.submitted_at = judged_at
        attempt.status = ExamAttemptStatus.PENDING_REVIEW if has_manual_questions else ExamAttemptStatus.GRADED
        attempt.graded_at = judged_at if not has_manual_questions else None
        attempt.graded_by = None
        await attempt.save()

        return await self.get_my_attempt_detail(attempt.id, user_id)

    async def list_my_attempts(self, user_id: int, page: int, page_size: int, title: str | None = None):
        q = Q(user_id=user_id)
        if title:
            paper_ids = await ExamPaper.filter(title__contains=title).values_list("id", flat=True)
            q &= Q(paper_id__in=list(paper_ids))

        total, attempt_objs = await self.list(page=page, page_size=page_size, search=q, order=["-id"])
        paper_ids = [item.paper_id for item in attempt_objs]
        paper_map = {
            item["id"]: item for item in await ExamPaper.filter(id__in=paper_ids).values("id", "title", "status", "total_score")
        }
        data = []
        for attempt in attempt_objs:
            item = await attempt.to_dict()
            item["paper"] = paper_map.get(attempt.paper_id, {})
            data.append(item)
        return total, data

    async def get_my_attempt_detail(self, attempt_id: int, user_id: int):
        attempt = await self._get_owned_attempt(attempt_id, user_id)
        reveal_answer = attempt.status != ExamAttemptStatus.IN_PROGRESS
        return await self._serialize_attempt(attempt, reveal_answer=reveal_answer)

    async def get_attempt_detail_for_grading(self, attempt_id: int):
        attempt = await self.get(id=attempt_id)
        data = await self._serialize_attempt(attempt, reveal_answer=True)
        user = await User.filter(id=attempt.user_id).first()
        data["user"] = await user.to_dict(exclude_fields=["password"]) if user else {}
        return data


exam_attempt_controller = ExamAttemptController()
