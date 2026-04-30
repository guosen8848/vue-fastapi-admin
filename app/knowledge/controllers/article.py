from datetime import datetime

from fastapi import HTTPException
from fastapi import UploadFile
from tortoise.expressions import Q

from app.core.crud import CRUDBase
from app.knowledge.constants import KnowledgeArticleBlockType, KnowledgeArticleStatus
from app.knowledge.models import KnowledgeArticle, KnowledgeArticleBlock, KnowledgeCategory
from app.knowledge.schemas.article import KnowledgeArticleCreate, KnowledgeArticleUpdate
from app.knowledge.schemas.block import KnowledgeArticleBlockPayload
from app.knowledge.storage import (
    finalize_temp_upload,
    get_storage_abspath,
    load_temp_upload,
    remove_stored_file,
    save_temp_upload,
)
from app.models.admin import User


class KnowledgeArticleController(CRUDBase[KnowledgeArticle, KnowledgeArticleCreate, KnowledgeArticleUpdate]):
    def __init__(self):
        super().__init__(model=KnowledgeArticle)

    async def _validate_category(self, category_id: int, active_only: bool = False):
        query = KnowledgeCategory.filter(id=category_id)
        if active_only:
            query = query.filter(is_active=True)
        category = await query.first()
        if not category:
            raise HTTPException(status_code=404, detail="所属分类不存在")
        return category

    async def _get_category_filter_ids(self, category_id: int, active_only: bool = False):
        await self._validate_category(category_id, active_only=active_only)
        query = KnowledgeCategory.filter(Q(id=category_id) | Q(parent_id=category_id))
        if active_only:
            query = query.filter(is_active=True)
        category_ids = await query.values_list("id", flat=True)
        return list(category_ids)

    async def _serialize_block(self, block: KnowledgeArticleBlock):
        return await block.to_dict(exclude_fields=["file_path"])

    async def _is_admin_user(self, user_id: int):
        user = await User.filter(id=user_id).first()
        roles = await user.roles if user else []
        return bool(user and user.is_superuser) or any(role.name == "管理员" for role in roles)

    async def _ensure_article_access(self, article: KnowledgeArticle, user_id: int | None):
        if user_id is None:
            return
        if await self._is_admin_user(user_id):
            return
        if article.created_by != user_id:
            raise HTTPException(status_code=404, detail="文章不存在")

    async def _get_publisher(self, user_id: int | None):
        if not user_id:
            return {}
        user = await User.filter(id=user_id).first()
        if not user:
            return {}
        return {
            "id": user.id,
            "username": user.username,
            "alias": user.alias,
        }

    def _build_plain_content(self, blocks: list[KnowledgeArticleBlockPayload] | None, fallback_content: str):
        if not blocks:
            return fallback_content.strip()

        fragments = []
        for block in blocks:
            if block.block_type == KnowledgeArticleBlockType.TEXT:
                text_content = (block.text_content or "").strip()
                if text_content:
                    fragments.append(text_content)
                continue

            file_name = (block.file_name or "").strip()
            if file_name:
                fragments.append(file_name)

        return "\n\n".join(fragments).strip() or fallback_content.strip()

    def _build_fallback_text_block(self, article: KnowledgeArticle):
        if not article.content.strip():
            return []
        return [
            KnowledgeArticleBlockPayload(
                block_type=KnowledgeArticleBlockType.TEXT,
                text_content=article.content,
            ).model_dump()
        ]

    def _normalize_blocks(self, blocks: list[KnowledgeArticleBlockPayload] | None, fallback_content: str):
        if blocks is None and fallback_content.strip():
            return [
                KnowledgeArticleBlockPayload(
                    block_type=KnowledgeArticleBlockType.TEXT,
                    text_content=fallback_content,
                )
            ]
        return blocks or []

    async def _get_article_blocks(self, article: KnowledgeArticle):
        block_objs = await KnowledgeArticleBlock.filter(article_id=article.id).order_by("sort_order", "id")
        if not block_objs:
            return self._build_fallback_text_block(article)
        return [await self._serialize_block(block) for block in block_objs]

    async def _sync_article_blocks(
        self,
        article: KnowledgeArticle,
        blocks: list[KnowledgeArticleBlockPayload] | None,
        fallback_content: str,
    ):
        if blocks is None:
            return

        existing_blocks = await KnowledgeArticleBlock.filter(article_id=article.id).order_by("sort_order", "id")
        existing_map = {block.id: block for block in existing_blocks}
        keep_ids: set[int] = set()

        normalized_blocks = self._normalize_blocks(blocks, fallback_content)

        for sort_order, block in enumerate(normalized_blocks, start=1):
            block_type = KnowledgeArticleBlockType(block.block_type)
            existing_block = existing_map.get(block.id) if block.id else None

            if block_type == KnowledgeArticleBlockType.TEXT:
                text_content = (block.text_content or "").strip()
                if not text_content:
                    continue

                if existing_block and existing_block.block_type == KnowledgeArticleBlockType.TEXT:
                    existing_block.update_from_dict(
                        {
                            "sort_order": sort_order,
                            "text_content": text_content,
                            "file_name": None,
                            "file_ext": None,
                            "mime_type": None,
                            "file_size": None,
                            "render_html": None,
                            "render_json": None,
                            "extra_meta": None,
                        }
                    )
                    await existing_block.save()
                    keep_ids.add(existing_block.id)
                    continue

                await KnowledgeArticleBlock.create(
                    article_id=article.id,
                    block_type=KnowledgeArticleBlockType.TEXT,
                    sort_order=sort_order,
                    text_content=text_content,
                )
                continue

            if block.temp_token:
                finalized = finalize_temp_upload(block.temp_token, article.id)
                await KnowledgeArticleBlock.create(
                    article_id=article.id,
                    block_type=block_type,
                    sort_order=sort_order,
                    file_name=finalized["file_name"],
                    file_ext=finalized["file_ext"],
                    mime_type=finalized["mime_type"],
                    file_size=finalized["file_size"],
                    file_path=finalized["file_path"],
                    render_html=finalized.get("render_html"),
                    render_json=finalized.get("render_json"),
                    extra_meta=finalized.get("extra_meta"),
                )
                continue

            if existing_block and existing_block.block_type == block_type:
                existing_block.update_from_dict({"sort_order": sort_order})
                await existing_block.save()
                keep_ids.add(existing_block.id)
                continue

            raise HTTPException(status_code=400, detail="文件内容块数据无效，请重新上传后再保存")

        for existing_block in existing_blocks:
            if existing_block.id in keep_ids:
                continue
            remove_stored_file(existing_block.file_path)
            await existing_block.delete()

    async def list_articles(
        self,
        page: int,
        page_size: int,
        title: str | None = None,
        category_id: int | None = None,
        status: KnowledgeArticleStatus | None = None,
        is_top: bool | None = None,
        active_only: bool = False,
        user_id: int | None = None,
    ):
        q = Q()
        if title:
            q &= Q(title__contains=title)
        if category_id is not None:
            category_ids = await self._get_category_filter_ids(category_id, active_only=active_only)
            q &= Q(category_id__in=category_ids)
        if status:
            q &= Q(status=status)
        if is_top is not None:
            q &= Q(is_top=is_top)
        if active_only:
            active_category_ids = await KnowledgeCategory.filter(is_active=True).values_list("id", flat=True)
            q &= Q(category_id__in=list(active_category_ids))
        if user_id is not None and not await self._is_admin_user(user_id):
            q &= Q(created_by=user_id)

        total, article_objs = await self.list(
            page=page,
            page_size=page_size,
            search=q,
            order=["-is_top", "-published_at", "-id"],
        )
        data = [await obj.to_dict() for obj in article_objs]
        category_ids = list({item["category_id"] for item in data})
        categories = []
        if category_ids:
            categories = await KnowledgeCategory.filter(id__in=category_ids).values("id", "name", "parent_id")
        category_map = {item["id"]: item for item in categories}
        publisher_ids = list({item["created_by"] for item in data if item.get("created_by")})
        publishers = []
        if publisher_ids:
            publishers = await User.filter(id__in=publisher_ids).values("id", "username", "alias")
        publisher_map = {item["id"]: item for item in publishers}

        for item in data:
            item["category"] = category_map.get(item["category_id"], {})
            item["publisher"] = publisher_map.get(item.get("created_by"), {})

        return total, data

    async def get_article_detail(
        self,
        article_id: int,
        status: KnowledgeArticleStatus | None = None,
        active_only: bool = False,
        user_id: int | None = None,
    ):
        article = await self.get(id=article_id)
        await self._ensure_article_access(article, user_id)
        if status and article.status != status:
            raise HTTPException(status_code=404, detail="文章不存在")
        category = await self._validate_category(article.category_id, active_only=active_only)
        data = await article.to_dict()
        data["category"] = {"id": category.id, "name": category.name, "parent_id": category.parent_id}
        data["publisher"] = await self._get_publisher(article.created_by)
        data["blocks"] = await self._get_article_blocks(article)
        return data

    async def create_article(self, obj_in: KnowledgeArticleCreate, user_id: int):
        await self._validate_category(obj_in.category_id)
        blocks = self._normalize_blocks(obj_in.blocks, obj_in.content)

        obj_dict = obj_in.model_dump(exclude={"blocks"})
        obj_dict["content"] = self._build_plain_content(blocks, obj_in.content)
        obj_dict["published_at"] = datetime.now() if obj_in.status == KnowledgeArticleStatus.PUBLISHED else None
        obj_dict["is_top"] = obj_in.is_top if await self._is_admin_user(user_id) else False
        obj_dict["created_by"] = user_id
        obj_dict["updated_by"] = user_id
        article = await self.create(obj_in=obj_dict)
        await self._sync_article_blocks(article=article, blocks=blocks, fallback_content=obj_dict["content"])
        return article

    async def update_article(self, obj_in: KnowledgeArticleUpdate, user_id: int):
        article = await self.get(id=obj_in.id)
        await self._ensure_article_access(article, user_id)
        await self._validate_category(obj_in.category_id)

        blocks = obj_in.blocks
        content = self._build_plain_content(blocks, obj_in.content)
        obj_dict = obj_in.model_dump(exclude={"blocks"})
        obj_dict["content"] = content
        if obj_in.status == KnowledgeArticleStatus.PUBLISHED:
            obj_dict["published_at"] = article.published_at or datetime.now()
        else:
            obj_dict["published_at"] = None
        if not await self._is_admin_user(user_id):
            obj_dict["is_top"] = article.is_top
        obj_dict["updated_by"] = user_id
        article = await self.update(id=obj_in.id, obj_in=obj_dict)
        await self._sync_article_blocks(article=article, blocks=blocks, fallback_content=content)
        return article

    async def upload_article_block(self, file: UploadFile):
        return await save_temp_upload(file)

    async def delete_article(self, article_id: int, user_id: int | None = None):
        article = await self.get(id=article_id)
        await self._ensure_article_access(article, user_id)
        blocks = await KnowledgeArticleBlock.filter(article_id=article_id).all()
        for block in blocks:
            remove_stored_file(block.file_path)
            await block.delete()
        await article.delete()

    async def get_block_file(
        self,
        block_id: int | None = None,
        temp_token: str | None = None,
        status: KnowledgeArticleStatus | None = None,
        active_only: bool = False,
        user_id: int | None = None,
    ):
        if temp_token:
            temp_data = load_temp_upload(temp_token)
            return {
                "path": get_storage_abspath(temp_data["file_path"]),
                "file_name": temp_data["file_name"],
                "mime_type": temp_data["mime_type"],
            }

        if block_id is None:
            raise HTTPException(status_code=400, detail="缺少文件标识")

        block = await KnowledgeArticleBlock.get_or_none(id=block_id)
        if not block or not block.file_path:
            raise HTTPException(status_code=404, detail="文件不存在")

        article = await self.get(id=block.article_id)
        await self._ensure_article_access(article, user_id)
        if status and article.status != status:
            raise HTTPException(status_code=404, detail="文件不存在")
        await self._validate_category(article.category_id, active_only=active_only)

        file_path = get_storage_abspath(block.file_path)
        if not file_path.exists():
            raise HTTPException(status_code=404, detail="文件不存在")

        return {
            "path": file_path,
            "file_name": block.file_name,
            "mime_type": block.mime_type or "application/octet-stream",
        }


knowledge_article_controller = KnowledgeArticleController()
