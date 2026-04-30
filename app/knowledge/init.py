from app.controllers.api import api_controller
from app.models.admin import Api, Menu
from app.schemas.menus import MenuType


async def init_knowledge_menus():
    root_menu = await Menu.filter(path="/knowledge", parent_id=0).first()
    if not root_menu:
        root_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="知识库管理",
            path="/knowledge",
            order=3,
            parent_id=0,
            icon="material-symbols:menu-book-outline",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/knowledge/category",
        )

    children = [
        dict(
            menu_type=MenuType.MENU,
            name="知识分类",
            path="category",
            order=1,
            parent_id=root_menu.id,
            icon="material-symbols:category-outline",
            is_hidden=False,
            component="/knowledge/category",
            keepalive=False,
        ),
        dict(
            menu_type=MenuType.MENU,
            name="知识文章",
            path="article",
            order=2,
            parent_id=root_menu.id,
            icon="material-symbols:article-outline",
            is_hidden=False,
            component="/knowledge/article",
            keepalive=False,
        ),
        dict(
            menu_type=MenuType.MENU,
            name="知识浏览",
            path="published",
            order=3,
            parent_id=root_menu.id,
            icon="material-symbols:auto-stories-outline",
            is_hidden=False,
            component="/knowledge/published",
            keepalive=False,
        ),
    ]

    for child in children:
        exists = await Menu.filter(parent_id=root_menu.id, path=child["path"]).exists()
        if not exists:
            await Menu.create(**child)


async def init_knowledge_apis():
    required_apis = [
        ("GET", "/api/v1/knowledge/category/list"),
        ("GET", "/api/v1/knowledge/category/get"),
        ("POST", "/api/v1/knowledge/category/create"),
        ("POST", "/api/v1/knowledge/category/update"),
        ("DELETE", "/api/v1/knowledge/category/delete"),
        ("GET", "/api/v1/knowledge/article/list"),
        ("GET", "/api/v1/knowledge/article/get"),
        ("POST", "/api/v1/knowledge/article/create"),
        ("POST", "/api/v1/knowledge/article/update"),
        ("DELETE", "/api/v1/knowledge/article/delete"),
        ("GET", "/api/v1/knowledge/published/category/list"),
        ("GET", "/api/v1/knowledge/published/article/list"),
        ("GET", "/api/v1/knowledge/published/article/get"),
        ("POST", "/api/v1/knowledge/article/block/upload"),
        ("GET", "/api/v1/knowledge/article/block/file"),
        ("GET", "/api/v1/knowledge/published/article/block/file"),
    ]
    exists = True
    for method, path in required_apis:
        api_exists = await Api.filter(tags="知识库模块", method=method, path=path).exists()
        if not api_exists:
            exists = False
            break
    if not exists:
        await api_controller.refresh_api()


async def init_knowledge_data():
    await init_knowledge_menus()
    await init_knowledge_apis()
