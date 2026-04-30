from fastapi import HTTPException
from tortoise.expressions import Q
from tortoise.transactions import in_transaction

from app.core.crud import CRUDBase
from app.exam.constants import ExamAttemptStatus
from app.exam.models import ExamAttempt, ExamPaper, ExamPaperQuestion
from app.exam.schemas.paper import ExamPaperCreate, ExamPaperUpdate
from app.exam.utils import round_score
from app.models.admin import User

from .question import exam_question_controller


class ExamPaperController(CRUDBase[ExamPaper, ExamPaperCreate, ExamPaperUpdate]):
    def __init__(self):
        super().__init__(model=ExamPaper)

    async def _build_paper_questions(self, question_items: list[dict]):
        if not question_items:
            raise HTTPException(status_code=400, detail="试卷至少需要选择一道题目")

        normalized_items = sorted(question_items, key=lambda item: (item["sort_order"], item["question_id"]))
        question_ids = [item["question_id"] for item in normalized_items]
        if len(question_ids) != len(set(question_ids)):
            raise HTTPException(status_code=400, detail="同一试卷中不能重复添加题目")

        question_map = await exam_question_controller.get_questions_by_ids(question_ids, active_only=True)
        results = []
        for item in normalized_items:
            question = question_map[item["question_id"]]
            snapshot = await exam_question_controller.build_snapshot(question)
            results.append(
                {
                    "question_id": question.id,
                    "sort_order": int(item["sort_order"]),
                    "score": round_score(item["score"]),
                    "snapshot": snapshot,
                }
            )
        return results

    async def _serialize_paper(self, paper: ExamPaper, include_questions: bool = False):
        data = await paper.to_dict()
        data["has_attempts"] = await ExamAttempt.filter(paper_id=paper.id).exists()
        if not include_questions:
            return data

        question_rows = await ExamPaperQuestion.filter(paper_id=paper.id).order_by("sort_order", "id")
        data["questions"] = []
        for row in question_rows:
            item = await row.to_dict()
            item["question_snapshot"] = row.question_snapshot or {}
            data["questions"].append(item)
        return data

    async def list_papers(
        self,
        page: int,
        page_size: int,
        title: str | None = None,
        status: str | None = None,
        is_active: bool | None = None,
    ):
        q = Q()
        if title:
            q &= Q(title__contains=title)
        if status:
            q &= Q(status=status)
        if is_active is not None:
            q &= Q(is_active=is_active)

        total, paper_objs = await self.list(page=page, page_size=page_size, search=q, order=["-id"])
        data = [await self._serialize_paper(obj) for obj in paper_objs]
        return total, data

    async def get_paper_detail(self, paper_id: int):
        paper = await self.get(id=paper_id)
        return await self._serialize_paper(paper, include_questions=True)

    async def get_paper_attempts(self, paper_id: int):
        paper = await self.get(id=paper_id)
        attempts = await ExamAttempt.filter(paper_id=paper_id).order_by("-id").all()

        user_ids = {attempt.user_id for attempt in attempts}
        reviewer_ids = {attempt.graded_by for attempt in attempts if attempt.graded_by}
        claimed_ids = {attempt.claimed_by for attempt in attempts if attempt.claimed_by}
        related_user_ids = user_ids | reviewer_ids | claimed_ids
        user_rows = (
            await User.filter(id__in=list(related_user_ids)).values("id", "username", "alias")
            if related_user_ids
            else []
        )
        user_map = {item["id"]: item for item in user_rows}

        status_counts = {
            "in_progress_count": 0,
            "submitted_count": 0,
            "pending_review_count": 0,
            "graded_count": 0,
        }
        graded_scores = []
        pass_count = 0
        attempt_rows = []

        for attempt in attempts:
            item = await attempt.to_dict()
            status = attempt.status
            if status == ExamAttemptStatus.IN_PROGRESS:
                status_counts["in_progress_count"] += 1
            else:
                status_counts["submitted_count"] += 1
            if status == ExamAttemptStatus.PENDING_REVIEW:
                status_counts["pending_review_count"] += 1
            if status == ExamAttemptStatus.GRADED:
                status_counts["graded_count"] += 1
                graded_scores.append(attempt.total_score)
                if attempt.total_score >= paper.pass_score:
                    pass_count += 1

            item["user"] = user_map.get(attempt.user_id, {})
            item["graded_by_user"] = user_map.get(attempt.graded_by, {}) if attempt.graded_by else {}
            item["claimed_by_user"] = user_map.get(attempt.claimed_by, {}) if attempt.claimed_by else {}
            item["is_passed"] = status == ExamAttemptStatus.GRADED and attempt.total_score >= paper.pass_score
            attempt_rows.append(item)

        graded_count = status_counts["graded_count"]
        summary = {
            "attempt_count": len(attempts),
            **status_counts,
            "pass_count": pass_count,
            "pass_rate": round_score((pass_count / graded_count * 100) if graded_count else 0),
            "average_score": round_score(sum(graded_scores) / graded_count if graded_count else 0),
            "max_score": round_score(max(graded_scores) if graded_scores else 0),
        }

        return {
            "paper": await paper.to_dict(),
            "summary": summary,
            "attempts": attempt_rows,
        }

    async def create_paper(self, obj_in: ExamPaperCreate, user_id: int):
        question_items = await self._build_paper_questions([item.model_dump() for item in obj_in.questions])
        total_score = round_score(sum(item["score"] for item in question_items))
        if obj_in.pass_score > total_score:
            raise HTTPException(status_code=400, detail="及格分不能大于试卷总分")

        payload = obj_in.model_dump(exclude={"questions"})
        payload["total_score"] = total_score
        payload["question_count"] = len(question_items)
        payload["created_by"] = user_id
        payload["updated_by"] = user_id

        async with in_transaction() as connection:
            paper = await ExamPaper.create(**payload, using_db=connection)
            for item in question_items:
                await ExamPaperQuestion.create(
                    paper_id=paper.id,
                    question_id=item["question_id"],
                    sort_order=item["sort_order"],
                    score=item["score"],
                    question_snapshot=item["snapshot"],
                    using_db=connection,
                )
        return paper

    async def update_paper(self, obj_in: ExamPaperUpdate, user_id: int):
        paper = await self.get(id=obj_in.id)
        question_items = await self._build_paper_questions([item.model_dump() for item in obj_in.questions])
        total_score = round_score(sum(item["score"] for item in question_items))
        if obj_in.pass_score > total_score:
            raise HTTPException(status_code=400, detail="及格分不能大于试卷总分")

        payload = obj_in.model_dump(exclude={"questions"})
        payload["total_score"] = total_score
        payload["question_count"] = len(question_items)
        payload["updated_by"] = user_id

        existing_rows = await ExamPaperQuestion.filter(paper_id=paper.id).all()
        existing_map = {row.question_id: row for row in existing_rows}
        existing_ids = set(existing_map)
        new_ids = {item["question_id"] for item in question_items}
        has_attempts = await ExamAttempt.filter(paper_id=paper.id).exists()

        async with in_transaction() as connection:
            if has_attempts and existing_ids != new_ids:
                raise HTTPException(status_code=400, detail="已有答卷的试卷不允许调整题目集合")

            if has_attempts:
                for item in question_items:
                    row = existing_map[item["question_id"]]
                    row.update_from_dict(
                        {
                            "sort_order": item["sort_order"],
                            "score": item["score"],
                            "question_snapshot": item["snapshot"],
                        }
                    )
                    await row.save(using_db=connection)
            else:
                await ExamPaperQuestion.filter(paper_id=paper.id).using_db(connection).delete()
                for item in question_items:
                    await ExamPaperQuestion.create(
                        paper_id=paper.id,
                        question_id=item["question_id"],
                        sort_order=item["sort_order"],
                        score=item["score"],
                        question_snapshot=item["snapshot"],
                        using_db=connection,
                    )

            paper.update_from_dict(payload)
            await paper.save(using_db=connection)

        return paper

    async def delete_paper(self, paper_id: int):
        has_attempts = await ExamAttempt.filter(paper_id=paper_id).exists()
        if has_attempts:
            raise HTTPException(status_code=400, detail="试卷已有答卷记录，无法删除")
        await ExamPaperQuestion.filter(paper_id=paper_id).delete()
        await self.remove(id=paper_id)

    async def publish_paper(self, paper_id: int):
        paper = await self.get(id=paper_id)
        paper.status = "published"
        await paper.save()
        return paper

    async def close_paper(self, paper_id: int):
        paper = await self.get(id=paper_id)
        paper.status = "closed"
        await paper.save()
        return paper


exam_paper_controller = ExamPaperController()
