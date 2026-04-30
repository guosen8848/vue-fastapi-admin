from tortoise import fields

from app.knowledge.constants import KnowledgeArticleBlockType, KnowledgeArticleStatus
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


class KnowledgeArticleBlock(BaseModel, TimestampMixin):
    article_id = fields.IntField(description="文章ID", index=True)
    block_type = fields.CharEnumField(KnowledgeArticleBlockType, description="内容块类型", index=True)
    sort_order = fields.IntField(default=0, description="排序", index=True)
    text_content = fields.TextField(null=True, description="文本内容")
    file_name = fields.CharField(max_length=255, null=True, description="原始文件名")
    file_ext = fields.CharField(max_length=20, null=True, description="文件扩展名")
    mime_type = fields.CharField(max_length=100, null=True, description="文件MIME类型")
    file_size = fields.BigIntField(null=True, description="文件大小")
    file_path = fields.CharField(max_length=500, null=True, description="文件相对路径")
    render_html = fields.TextField(null=True, description="HTML预览内容")
    render_json = fields.JSONField(null=True, description="结构化预览内容")
    extra_meta = fields.JSONField(null=True, description="额外元数据")

    class Meta:
        table = "knowledge_article_block"
