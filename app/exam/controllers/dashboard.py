from app.core.crud import CRUDBase
from app.exam.constants import ExamAttemptStatus, ExamPaperStatus, ExamPracticeSessionStatus
from app.exam.models import (
    ExamAttempt,
    ExamBank,
    ExamPaper,
    ExamPracticeSession,
    ExamPracticeWrongQuestion,
    ExamQuestion,
)
from app.models.admin import User


class ExamDashboardController(CRUDBase[ExamAttempt, dict, dict]):
    def __init__(self):
        super().__init__(model=ExamAttempt)

    async def get_dashboard(self, user_id: int):
        user = await User.filter(id=user_id).first()
        roles = await user.roles if user else []
        is_admin = bool(user and user.is_superuser) or any(role.name == "管理员" for role in roles)

        if is_admin:
            return await self._get_admin_dashboard()
        return await self._get_user_dashboard(user_id=user_id)

    async def _get_admin_dashboard(self):
        pending_attempts = await ExamAttempt.filter(status=ExamAttemptStatus.PENDING_REVIEW).order_by("-id").limit(6)
        recent_papers = await ExamPaper.all().order_by("-id").limit(6)

        return {
            "role": "admin",
            "stats": {
                "bank_count": await ExamBank.all().count(),
                "question_count": await ExamQuestion.all().count(),
                "published_paper_count": await ExamPaper.filter(
                    status=ExamPaperStatus.PUBLISHED,
                    is_active=True,
                ).count(),
                "pending_grading_count": await ExamAttempt.filter(status=ExamAttemptStatus.PENDING_REVIEW).count(),
            },
            "pending_gradings": await self._serialize_attempts(pending_attempts, include_user=True),
            "recent_papers": [await paper.to_dict() for paper in recent_papers],
        }

    async def _get_user_dashboard(self, user_id: int):
        published_paper_ids = list(
            await ExamPaper.filter(status=ExamPaperStatus.PUBLISHED, is_active=True).values_list("id", flat=True)
        )
        paper_attempts = []
        if published_paper_ids:
            paper_attempts = await ExamAttempt.filter(user_id=user_id, paper_id__in=published_paper_ids).all()
        attempt_map = {attempt.paper_id: attempt for attempt in paper_attempts}
        available_count = sum(
            1
            for paper_id in published_paper_ids
            if paper_id not in attempt_map or attempt_map[paper_id].status == ExamAttemptStatus.IN_PROGRESS
        )

        available_papers = await ExamPaper.filter(
            status=ExamPaperStatus.PUBLISHED,
            is_active=True,
        ).order_by("-id").limit(6)
        recent_attempts = await ExamAttempt.filter(user_id=user_id).order_by("-id").limit(6)
        recent_practices = await ExamPracticeSession.filter(user_id=user_id).order_by("-id").limit(6)
        practice_rows = await ExamPracticeSession.filter(user_id=user_id).values("answered_count", "correct_count")
        answered_count = sum(row["answered_count"] or 0 for row in practice_rows)
        correct_count = sum(row["correct_count"] or 0 for row in practice_rows)

        return {
            "role": "user",
            "stats": {
                "available_paper_count": available_count,
                "in_progress_attempt_count": await ExamAttempt.filter(
                    user_id=user_id,
                    status=ExamAttemptStatus.IN_PROGRESS,
                ).count(),
                "pending_review_count": await ExamAttempt.filter(
                    user_id=user_id,
                    status=ExamAttemptStatus.PENDING_REVIEW,
                ).count(),
                "completed_practice_count": await ExamPracticeSession.filter(
                    user_id=user_id,
                    status=ExamPracticeSessionStatus.COMPLETED,
                ).count(),
                "wrong_question_count": await ExamPracticeWrongQuestion.filter(
                    user_id=user_id,
                    mastered_at__isnull=True,
                ).count(),
                "practice_accuracy": round(correct_count / answered_count * 100) if answered_count else 0,
            },
            "available_papers": await self._serialize_papers_with_attempt(available_papers, attempt_map),
            "recent_attempts": await self._serialize_attempts(recent_attempts),
            "recent_practices": [await practice.to_dict() for practice in recent_practices],
        }

    async def _serialize_papers_with_attempt(self, papers, attempt_map: dict[int, ExamAttempt]):
        data = []
        for paper in papers:
            item = await paper.to_dict()
            attempt = attempt_map.get(paper.id)
            item["attempt"] = await attempt.to_dict() if attempt else None
            data.append(item)
        return data

    async def _serialize_attempts(self, attempts, include_user: bool = False):
        paper_ids = [attempt.paper_id for attempt in attempts]
        user_ids = [attempt.user_id for attempt in attempts]
        paper_map = {}
        if paper_ids:
            paper_map = {
                item["id"]: item
                for item in await ExamPaper.filter(id__in=paper_ids).values("id", "title", "total_score")
            }
        user_map = {}
        if include_user and user_ids:
            user_map = {item["id"]: item for item in await User.filter(id__in=user_ids).values("id", "username")}

        data = []
        for attempt in attempts:
            item = await attempt.to_dict()
            item["paper"] = paper_map.get(attempt.paper_id, {})
            if include_user:
                item["user"] = user_map.get(attempt.user_id, {})
            data.append(item)
        return data


exam_dashboard_controller = ExamDashboardController()
