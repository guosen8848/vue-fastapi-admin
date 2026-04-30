from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.exam.constants import ExamDifficulty, ExamQuestionType


class ExamPracticeStartPayload(BaseModel):
    bank_id: Optional[int] = Field(None, description="题库ID")
    question_type: Optional[ExamQuestionType] = Field(None, description="题型")
    difficulty: Optional[ExamDifficulty] = Field(None, description="难度")
    question_count: int = Field(10, description="题目数量", ge=1, le=100)
    question_ids: list[int] = Field(default_factory=list, description="指定题目ID")

    @field_validator("question_ids")
    @classmethod
    def dedupe_question_ids(cls, value: list[int]):
        return list(dict.fromkeys([int(item) for item in value if int(item) > 0]))


class ExamPracticeAnswerPayload(BaseModel):
    answer_id: int = Field(..., description="练习答案ID")
    answer_payload: object = Field(None, description="答案内容")


class ExamPracticeActionPayload(BaseModel):
    session_id: int = Field(..., description="练习ID")
