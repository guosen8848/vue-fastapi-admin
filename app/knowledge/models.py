from tortoise import fields

from app.knowledge.constants import KnowledgeArticleStatus
from app.models.base import BaseModel, TimestampMixin


class KnowledgeCategory(BaseModel, TimestampMixin):
    name = fields.CharField(max_length=50, unique=True, description="分类名称", index=True)
    desc = fields.CharField(max_length=500, null=True, description="分类说明")
    order = fields.IntField(default=0, description="排序", index=True)
    parent_id = fields.IntField(default=0, description="父分类ID", index=True)
    is_active = fields.BooleanField(default=True, description="是否启用", index=True)

    class Meta:
        table = "knowledge_category"


class KnowledgeArticle(BaseModel, TimestampMixin):
    title = fields.CharField(max_length=200, description="文章标题", index=True)
    summary = fields.TextField(null=True, description="文章摘要")
    content = fields.TextField(description="文章内容")
    tags = fields.JSONField(null=True, description="文章标签")
    status = fields.CharEnumField(
        KnowledgeArticleStatus,
        default=KnowledgeArticleStatus.DRAFT,
        description="文章状态",
        index=True,
    )
    is_top = fields.BooleanField(default=False, description="是否置顶", index=True)
    published_at = fields.DatetimeField(null=True, description="发布时间", index=True)
    category_id = fields.IntField(description="分类ID", index=True)
    created_by = fields.IntField(null=True, description="创建人ID", index=True)
    updated_by = fields.IntField(null=True, description="更新人ID", index=True)

    class Meta:
        table = "knowledge_article"
