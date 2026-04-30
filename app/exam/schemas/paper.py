from typing import Optional

from pydantic import BaseModel, Field

from app.exam.constants import ExamPaperStatus


class ExamPaperQuestionPayload(BaseModel):
    question_id: int = Field(..., description="题目ID")
    score: float = Field(..., description="分值", gt=0)
    sort_order: int = Field(..., description="排序", ge=1)


class ExamPaperBase(BaseModel):
    title: str = Field(..., description="试卷标题")
    desc: Optional[str] = Field(None, description="试卷说明")
    status: ExamPaperStatus = Field(default=ExamPaperStatus.DRAFT, description="试卷状态")
    duration_minutes: int = Field(0, description="限时分钟数", ge=0)
    pass_score: float = Field(0, description="及格分", ge=0)
    is_active: bool = Field(True, description="是否启用")
    questions: list[ExamPaperQuestionPayload] = Field(default_factory=list, description="试卷题目")


class ExamPaperCreate(ExamPaperBase):
    pass


class ExamPaperUpdate(ExamPaperBase):
    id: int


class ExamPaperActionPayload(BaseModel):
    paper_id: int = Field(..., description="试卷ID")
