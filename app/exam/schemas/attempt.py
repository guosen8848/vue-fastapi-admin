from typing import Any

from pydantic import BaseModel, Field


class ExamAttemptStartPayload(BaseModel):
    paper_id: int = Field(..., description="试卷ID")


class ExamAttemptAnswerPayload(BaseModel):
    paper_question_id: int = Field(..., description="试卷题目ID")
    answer_payload: Any = Field(default=None, description="用户答案")


class ExamAttemptSavePayload(BaseModel):
    attempt_id: int = Field(..., description="答卷ID")
    answers: list[ExamAttemptAnswerPayload] = Field(default_factory=list, description="作答列表")


class ExamAttemptSubmitPayload(BaseModel):
    attempt_id: int = Field(..., description="答卷ID")
    answers: list[ExamAttemptAnswerPayload] = Field(default_factory=list, description="作答列表")
