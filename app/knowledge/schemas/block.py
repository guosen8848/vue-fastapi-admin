from typing import Any

from pydantic import BaseModel, Field, field_validator

from app.knowledge.constants import KnowledgeArticleBlockType


class KnowledgeArticleBlockPayload(BaseModel):
    id: int | None = Field(None, description="内容块ID")
    block_type: KnowledgeArticleBlockType = Field(..., description="内容块类型")
    text_content: str | None = Field(None, description="文本块内容")
    temp_token: str | None = Field(None, description="临时上传令牌")
    file_name: str | None = Field(None, description="文件名称")
    file_ext: str | None = Field(None, description="文件扩展名")
    mime_type: str | None = Field(None, description="文件MIME类型")
    file_size: int | None = Field(None, description="文件大小")
    render_html: str | None = Field(None, description="HTML预览内容")
    render_json: dict[str, Any] | None = Field(None, description="结构化预览内容")
    extra_meta: dict[str, Any] | None = Field(None, description="额外元数据")

    @field_validator("text_content")
    @classmethod
    def normalize_text_content(cls, value: str | None):
        if value is None:
            return value
        return value.strip("\n")
