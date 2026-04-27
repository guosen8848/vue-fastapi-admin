from typing import Optional

from pydantic import BaseModel, Field


class KnowledgeCategoryBase(BaseModel):
    name: str = Field(..., description="分类名称", example="产品文档")
    desc: Optional[str] = Field(None, description="分类说明", example="产品相关文档")
    order: int = Field(0, description="排序")
    parent_id: int = Field(0, description="父分类ID")
    is_active: bool = Field(True, description="是否启用")


class KnowledgeCategoryCreate(KnowledgeCategoryBase):
    pass


class KnowledgeCategoryUpdate(KnowledgeCategoryBase):
    id: int
