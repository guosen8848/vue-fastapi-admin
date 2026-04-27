from fastapi import HTTPException

from app.knowledge.constants import KnowledgeArticleStatus
from app.core.crud import CRUDBase
from app.knowledge.models import KnowledgeArticle, KnowledgeCategory
from app.knowledge.schemas.category import KnowledgeCategoryCreate, KnowledgeCategoryUpdate


class KnowledgeCategoryController(CRUDBase[KnowledgeCategory, KnowledgeCategoryCreate, KnowledgeCategoryUpdate]):
    def __init__(self):
        super().__init__(model=KnowledgeCategory)

    async def get_category_tree(self):
        categories = await self.model.all().order_by("parent_id", "order", "id")

        def build_tree(parent_id: int):
            tree = []
            for category in categories:
                if category.parent_id != parent_id:
                    continue
                tree.append(
                    {
                        "id": category.id,
                        "name": category.name,
                        "desc": category.desc,
                        "order": category.order,
                        "parent_id": category.parent_id,
                        "is_active": category.is_active,
                        "created_at": category.created_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "updated_at": category.updated_at.strftime("%Y-%m-%d %H:%M:%S"),
                        "children": build_tree(category.id),
                    }
                )
            return tree

        return build_tree(0)

    async def get_published_category_tree(self):
        categories = await self.model.filter(is_active=True).order_by("parent_id", "order", "id")
        if not categories:
            return []

        published_article_rows = await KnowledgeArticle.filter(status=KnowledgeArticleStatus.PUBLISHED).values(
            "category_id"
        )

        category_map = {category.id: category for category in categories}
        direct_article_count = {}
        visible_ids = set()

        for row in published_article_rows:
            category_id = row["category_id"]
            if category_id not in category_map:
                continue

            direct_article_count[category_id] = direct_article_count.get(category_id, 0) + 1

            current_id = category_id
            while current_id and current_id in category_map and current_id not in visible_ids:
                visible_ids.add(current_id)
                current_id = category_map[current_id].parent_id

        def build_tree(parent_id: int):
            tree = []
            for category in categories:
                if category.parent_id != parent_id or category.id not in visible_ids:
                    continue

                children = build_tree(category.id)
                article_count = direct_article_count.get(category.id, 0) + sum(
                    child["article_count"] for child in children
                )
                tree.append(
                    {
                        "id": category.id,
                        "name": category.name,
                        "display_name": f"{category.name} ({article_count})",
                        "desc": category.desc,
                        "order": category.order,
                        "parent_id": category.parent_id,
                        "is_active": category.is_active,
                        "article_count": article_count,
                        "children": children,
                    }
                )
            return tree

        return build_tree(0)

    async def _validate_parent(self, parent_id: int, current_id: int | None = None):
        if parent_id == 0:
            return None
        if current_id and parent_id == current_id:
            raise HTTPException(status_code=400, detail="上级分类不能选择自己")
        parent = await self.model.filter(id=parent_id).first()
        if not parent:
            raise HTTPException(status_code=404, detail="上级分类不存在")
        if parent.parent_id != 0:
            raise HTTPException(status_code=400, detail="知识分类仅支持两级结构")
        return parent

    async def create_category(self, obj_in: KnowledgeCategoryCreate):
        await self._validate_parent(obj_in.parent_id)
        return await self.create(obj_in=obj_in)

    async def update_category(self, obj_in: KnowledgeCategoryUpdate):
        await self.get(id=obj_in.id)
        await self._validate_parent(obj_in.parent_id, current_id=obj_in.id)
        has_children = await self.model.filter(parent_id=obj_in.id).exists()
        if obj_in.parent_id != 0 and has_children:
            raise HTTPException(status_code=400, detail="存在子分类的根分类不能调整为子级分类")
        return await self.update(id=obj_in.id, obj_in=obj_in)

    async def delete_category(self, category_id: int):
        has_children = await self.model.filter(parent_id=category_id).exists()
        if has_children:
            raise HTTPException(status_code=400, detail="请先删除子分类后再删除当前分类")
        has_articles = await KnowledgeArticle.filter(category_id=category_id).exists()
        if has_articles:
            raise HTTPException(status_code=400, detail="当前分类下存在文章，无法删除")
        await self.remove(id=category_id)


knowledge_category_controller = KnowledgeCategoryController()
