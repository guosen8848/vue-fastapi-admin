from datetime import datetime

from fastapi import HTTPException
from tortoise.expressions import Q

from app.core.crud import CRUDBase
from app.exam.constants import ExamAttemptStatus, ExamJudgeStatus
from app.exam.models import ExamAnswer, ExamAttempt, ExamPaper
from app.exam.schemas.grading import ExamGradingClaimPayload, ExamGradingCompletePayload, ExamGradingScorePayload
from app.exam.utils import is_objective_question, normalize_optional_text, round_score
from app.models.admin import User

from .attempt import exam_attempt_controller


class ExamGradingController(CRUDBase[ExamAttempt, dict, dict]):
    def __init__(self):
        super().__init__(model=ExamAttempt)

    async def list_grading_attempts(
        self,
        page: int,
        page_size: int,
        paper_title: str | None = None,
        username: str | None = None,
        status: str | None = None,
    ):
        q = Q()
        if status:
            q &= Q(status=status)
        else:
            q &= Q(status=ExamAttemptStatus.PENDING_REVIEW)
        if paper_title:
            paper_ids = await ExamPaper.filter(title__contains=paper_title).values_list("id", flat=True)
            q &= Q(paper_id__in=list(paper_ids))
        if username:
            user_ids = await User.filter(username__contains=username).values_list("id", flat=True)
            q &= Q(user_id__in=list(user_ids))

        total, attempt_objs = await self.list(page=page, page_size=page_size, search=q, order=["-id"])
        paper_ids = [attempt.paper_id for attempt in attempt_objs]
        user_ids = [attempt.user_id for attempt in attempt_objs]
        paper_map = {item["id"]: item for item in await ExamPaper.filter(id__in=paper_ids).values("id", "title")}
        user_map = {item["id"]: item for item in await User.filter(id__in=user_ids).values("id", "username")}

        data = []
        for attempt in attempt_objs:
            item = await attempt.to_dict()
            item["paper"] = paper_map.get(attempt.paper_id, {})
            item["user"] = user_map.get(attempt.user_id, {})
            data.append(item)
        return total, data

    async def get_grading_detail(self, attempt_id: int):
        return await exam_attempt_controller.get_attempt_detail_for_grading(attempt_id)

    async def claim_grading(self, obj_in: ExamGradingClaimPayload, reviewer_id: int):
        attempt = await ExamAttempt.filter(id=obj_in.attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="答卷不存在")
        if attempt.status != ExamAttemptStatus.PENDING_REVIEW:
            raise HTTPException(status_code=400, detail="当前答卷不在待阅卷状态")
        if attempt.claimed_by and attempt.claimed_by != reviewer_id:
            raise HTTPException(status_code=400, detail=f"该答卷已被 {attempt.claimed_by_name or '其他管理员'} 领取")

        reviewer = await User.filter(id=reviewer_id).first()
        reviewer_name = reviewer.username if reviewer else str(reviewer_id)
        updated_count = await ExamAttempt.filter(id=attempt.id, status=ExamAttemptStatus.PENDING_REVIEW).filter(
            Q(claimed_by__isnull=True) | Q(claimed_by=reviewer_id)
        ).update(claimed_by=reviewer_id, claimed_by_name=reviewer_name)
        if not updated_count:
            attempt = await ExamAttempt.filter(id=obj_in.attempt_id).first()
            raise HTTPException(status_code=400, detail=f"该答卷已被 {attempt.claimed_by_name or '其他管理员'} 领取")
        return await self.get_grading_detail(obj_in.attempt_id)

    async def release_grading(self, obj_in: ExamGradingClaimPayload, reviewer_id: int):
        attempt = await ExamAttempt.filter(id=obj_in.attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="答卷不存在")
        if attempt.status != ExamAttemptStatus.PENDING_REVIEW:
            raise HTTPException(status_code=400, detail="当前答卷不在待阅卷状态")
        if not attempt.claimed_by:
            return await self.get_grading_detail(obj_in.attempt_id)
        if attempt.claimed_by != reviewer_id:
            raise HTTPException(status_code=400, detail=f"该答卷已被 {attempt.claimed_by_name or '其他管理员'} 领取")

        attempt.claimed_by = None
        attempt.claimed_by_name = None
        await attempt.save()
        return await self.get_grading_detail(obj_in.attempt_id)

    def ensure_claimed_by_reviewer(self, attempt: ExamAttempt, reviewer_id: int):
        if not attempt.claimed_by:
            raise HTTPException(status_code=400, detail="请先领取后再阅卷")
        if attempt.claimed_by != reviewer_id:
            raise HTTPException(status_code=400, detail=f"该答卷已被 {attempt.claimed_by_name or '其他管理员'} 领取")

    async def score_answer(self, obj_in: ExamGradingScorePayload, reviewer_id: int):
        answer = await ExamAnswer.filter(id=obj_in.answer_id).first()
        if not answer:
            raise HTTPException(status_code=404, detail="答案不存在")
        if is_objective_question(answer.question_type):
            raise HTTPException(status_code=400, detail="客观题不支持人工评分")

        attempt = await ExamAttempt.filter(id=answer.attempt_id).first()
        if not attempt or attempt.status != ExamAttemptStatus.PENDING_REVIEW:
            raise HTTPException(status_code=400, detail="当前答卷不在待阅卷状态")
        self.ensure_claimed_by_reviewer(attempt, reviewer_id)

        max_score = round_score((answer.answer_snapshot or {}).get("score"))
        if obj_in.manual_score > max_score:
            raise HTTPException(status_code=400, detail="人工得分不能大于本题分值")

        answer.manual_score = round_score(obj_in.manual_score)
        answer.final_score = answer.manual_score
        answer.reviewer_comment = normalize_optional_text(obj_in.reviewer_comment)
        answer.judge_status = ExamJudgeStatus.MANUAL_DONE
        answer.judged_at = datetime.now()
        answer.judged_by = reviewer_id
        await answer.save()
        return answer

    async def complete_grading(self, obj_in: ExamGradingCompletePayload, reviewer_id: int):
        attempt = await ExamAttempt.filter(id=obj_in.attempt_id).first()
        if not attempt:
            raise HTTPException(status_code=404, detail="答卷不存在")
        if attempt.status != ExamAttemptStatus.PENDING_REVIEW:
            raise HTTPException(status_code=400, detail="当前答卷不在待阅卷状态")
        self.ensure_claimed_by_reviewer(attempt, reviewer_id)

        answer_objs = await ExamAnswer.filter(attempt_id=attempt.id).all()
        subjective_score = 0.0
        for answer in answer_objs:
            if is_objective_question(answer.question_type):
                continue
            if answer.judge_status != ExamJudgeStatus.MANUAL_DONE:
                raise HTTPException(status_code=400, detail="仍有主观题未完成评分")
            subjective_score += answer.final_score

        attempt.subjective_score = round_score(subjective_score)
        attempt.total_score = round_score(attempt.objective_score + subjective_score)
        attempt.status = ExamAttemptStatus.GRADED
        attempt.graded_at = datetime.now()
        attempt.graded_by = reviewer_id
        attempt.claimed_by = None
        attempt.claimed_by_name = None
        await attempt.save()
        return attempt


exam_grading_controller = ExamGradingController()
