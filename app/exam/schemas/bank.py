from typing import Optional

from pydantic import BaseModel, Field


class ExamBankBase(BaseModel):
    name: str = Field(..., description="题库名称", example="Python 基础题库")
    desc: Optional[str] = Field(None, description="题库说明", example="用于新员工培训")
    is_active: bool = Field(True, description="是否启用")


class ExamBankCreate(ExamBankBase):
    pass


class ExamBankUpdate(ExamBankBase):
    id: int
