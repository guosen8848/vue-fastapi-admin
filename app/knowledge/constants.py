from enum import StrEnum


class KnowledgeArticleStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"


class KnowledgeArticleBlockType(StrEnum):
    TEXT = "text"
    MARKDOWN = "md"
    DOCX = "docx"
    PDF = "pdf"
    XLSX = "xlsx"


KNOWLEDGE_FILE_BLOCK_TYPES = {
    KnowledgeArticleBlockType.MARKDOWN,
    KnowledgeArticleBlockType.DOCX,
    KnowledgeArticleBlockType.PDF,
    KnowledgeArticleBlockType.XLSX,
}

KNOWLEDGE_ALLOWED_FILE_EXTENSIONS = {f".{block_type.value}" for block_type in KNOWLEDGE_FILE_BLOCK_TYPES}
