from typing import Optional

from pydantic import BaseModel, Field, field_validator

from app.exam.constants import ExamDifficulty, ExamQuestionType


class ExamQuestionOptionPayload(BaseModel):
    option_key: str = Field(..., description="选项键", example="A")
    option_content: str = Field(..., description="选项内容", example="FastAPI")


class ExamQuestionBase(BaseModel):
    bank_id: int = Field(..., description="题库ID")
    question_type: ExamQuestionType = Field(..., description="题型")
    category_path: Optional[str] = Field("", description="分类路径", example="Python/基础")
    stem: str = Field(..., description="题干")
    options: list[ExamQuestionOptionPayload] = Field(default_factory=list, description="选项列表")
    correct_answer: list[str] = Field(default_factory=list, description="标准答案")
    reference_answer: Optional[str] = Field(None, description="参考答案")
    analysis: Optional[str] = Field(None, description="解析")
    tags: list[str] = Field(default_factory=list, description="标签")
    difficulty: ExamDifficulty = Field(default=ExamDifficulty.MEDIUM, description="难度")
    default_score: float = Field(..., description="默认分值", ge=0)
    is_active: bool = Field(True, description="是否启用")

    @field_validator("category_path", "reference_answer", "analysis")
    @classmethod
    def normalize_optional_text(cls, value: str | None):
        if value is None:
            return value
        return value.strip()

    @field_validator("stem")
    @classmethod
    def normalize_stem(cls, value: str):
        return value.strip()


class ExamQuestionCreate(ExamQuestionBase):
    pass


class ExamQuestionUpdate(ExamQuestionBase):
    id: int
