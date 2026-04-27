from typing import Optional

from pydantic import BaseModel, Field

from app.knowledge.constants import KnowledgeArticleStatus


class KnowledgeArticleBase(BaseModel):
    title: str = Field(..., description="文章标题", example="如何创建用户")
    category_id: int = Field(..., description="所属分类ID")
    summary: Optional[str] = Field(None, description="文章摘要")
    content: str = Field(..., description="正文内容")
    tags: list[str] = Field(default_factory=list, description="文章标签")
    status: KnowledgeArticleStatus = Field(
        default=KnowledgeArticleStatus.DRAFT,
        description="文章状态",
    )
    is_top: bool = Field(False, description="是否置顶")


class KnowledgeArticleCreate(KnowledgeArticleBase):
    pass


class KnowledgeArticleUpdate(KnowledgeArticleBase):
    id: int
