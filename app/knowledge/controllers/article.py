from datetime import datetime

from fastapi import HTTPException
from tortoise.expressions import Q

from app.core.crud import CRUDBase
from app.knowledge.constants import KnowledgeArticleStatus
from app.knowledge.models import KnowledgeArticle, KnowledgeCategory
from app.knowledge.schemas.article import KnowledgeArticleCreate, KnowledgeArticleUpdate


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

    async def list_articles(
        self,
        page: int,
        page_size: int,
        title: str | None = None,
        category_id: int | None = None,
        status: KnowledgeArticleStatus | None = None,
        is_top: bool | None = None,
        active_only: bool = False,
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

        total, article_objs = await self.list(
            page=page,
            page_size=page_size,
            search=q,
            order=["-is_top", "-published_at", "-id"],
        )
        data = [await obj.to_dict() for obj in article_objs]
        category_ids = list({item["category_id"] for item in data})
        categories = await KnowledgeCategory.filter(id__in=category_ids).values("id", "name", "parent_id")
        category_map = {item["id"]: item for item in categories}

        for item in data:
            item["category"] = category_map.get(item["category_id"], {})

        return total, data

    async def get_article_detail(
        self,
        article_id: int,
        status: KnowledgeArticleStatus | None = None,
        active_only: bool = False,
    ):
        article = await self.get(id=article_id)
        if status and article.status != status:
            raise HTTPException(status_code=404, detail="文章不存在")
        category = await self._validate_category(article.category_id, active_only=active_only)
        data = await article.to_dict()
        data["category"] = {"id": category.id, "name": category.name, "parent_id": category.parent_id}
        return data

    async def create_article(self, obj_in: KnowledgeArticleCreate, user_id: int):
        await self._validate_category(obj_in.category_id)
        obj_dict = obj_in.model_dump()
        obj_dict["published_at"] = datetime.now() if obj_in.status == KnowledgeArticleStatus.PUBLISHED else None
        obj_dict["created_by"] = user_id
        obj_dict["updated_by"] = user_id
        return await self.create(obj_in=obj_dict)

    async def update_article(self, obj_in: KnowledgeArticleUpdate, user_id: int):
        article = await self.get(id=obj_in.id)
        await self._validate_category(obj_in.category_id)

        obj_dict = obj_in.model_dump()
        if obj_in.status == KnowledgeArticleStatus.PUBLISHED:
            obj_dict["published_at"] = article.published_at or datetime.now()
        else:
            obj_dict["published_at"] = None
        obj_dict["updated_by"] = user_id
        return await self.update(id=obj_in.id, obj_in=obj_dict)


knowledge_article_controller = KnowledgeArticleController()
