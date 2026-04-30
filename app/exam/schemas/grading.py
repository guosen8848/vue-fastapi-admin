from typing import Optional

from pydantic import BaseModel, Field


class ExamGradingScorePayload(BaseModel):
    answer_id: int = Field(..., description="答案ID")
    manual_score: float = Field(..., description="人工得分", ge=0)
    reviewer_comment: Optional[str] = Field(None, description="阅卷备注")


class ExamGradingCompletePayload(BaseModel):
    attempt_id: int = Field(..., description="答卷ID")


class ExamGradingClaimPayload(BaseModel):
    attempt_id: int = Field(..., description="答卷ID")
