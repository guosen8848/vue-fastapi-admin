from app.controllers.api import api_controller
from app.models.admin import Api, Menu, Role
from app.schemas.menus import MenuType
from tortoise.expressions import Q


async def init_exam_menus():
    root_menu = await Menu.filter(path="/exam", parent_id=0).first()
    if not root_menu:
        root_menu = await Menu.create(
            menu_type=MenuType.CATALOG,
            name="答题管理",
            path="/exam",
            order=4,
            parent_id=0,
            icon="material-symbols:quiz-outline-rounded",
            is_hidden=False,
            component="Layout",
            keepalive=False,
            redirect="/exam/answer",
        )

    children = [
        dict(
            menu_type=MenuType.MENU,
            name="题库管理",
            path="bank",
            order=1,
            parent_id=root_menu.id,
            icon="material-symbols:library-books-outline",
            is_hidden=False,
            component="/exam/bank",
            keepalive=False,
        ),
        dict(
            menu_type=MenuType.MENU,
            name="题目管理",
            path="question",
            order=2,
            parent_id=root_menu.id,
            icon="material-symbols:checklist-rtl-rounded",
            is_hidden=False,
            component="/exam/question",
            keepalive=False,
        ),
        dict(
            menu_type=MenuType.MENU,
            name="试卷管理",
            path="paper",
            order=3,
            parent_id=root_menu.id,
            icon="material-symbols:description-outline-rounded",
            is_hidden=False,
            component="/exam/paper",
            keepalive=False,
        ),
        dict(
            menu_type=MenuType.MENU,
            name="阅卷中心",
            path="grading",
            order=4,
            parent_id=root_menu.id,
            icon="material-symbols:grading-outline-rounded",
            is_hidden=False,
            component="/exam/grading",
            keepalive=False,
        ),
        dict(
            menu_type=MenuType.MENU,
            name="我的答题",
            path="answer",
            order=5,
            parent_id=root_menu.id,
            icon="material-symbols:edit-document",
            is_hidden=False,
            component="/exam/answer",
            keepalive=False,
        ),
        dict(
            menu_type=MenuType.MENU,
            name="练习中心",
            path="practice",
            order=6,
            parent_id=root_menu.id,
            icon="material-symbols:school-outline-rounded",
            is_hidden=False,
            component="/exam/practice",
            keepalive=False,
        ),
    ]

    for child in children:
        exists = await Menu.filter(parent_id=root_menu.id, path=child["path"]).exists()
        if not exists:
            await Menu.create(**child)


async def init_exam_apis():
    required_apis = [
        ("GET", "/api/v1/exam/dashboard"),
        ("GET", "/api/v1/exam/bank/list"),
        ("GET", "/api/v1/exam/bank/get"),
        ("POST", "/api/v1/exam/bank/create"),
        ("POST", "/api/v1/exam/bank/update"),
        ("DELETE", "/api/v1/exam/bank/delete"),
        ("GET", "/api/v1/exam/bank/template"),
        ("POST", "/api/v1/exam/bank/import"),
        ("GET", "/api/v1/exam/question/list"),
        ("GET", "/api/v1/exam/question/get"),
        ("POST", "/api/v1/exam/question/create"),
        ("POST", "/api/v1/exam/question/update"),
        ("DELETE", "/api/v1/exam/question/delete"),
        ("GET", "/api/v1/exam/paper/list"),
        ("GET", "/api/v1/exam/paper/get"),
        ("GET", "/api/v1/exam/paper/attempts"),
        ("POST", "/api/v1/exam/paper/create"),
        ("POST", "/api/v1/exam/paper/update"),
        ("DELETE", "/api/v1/exam/paper/delete"),
        ("POST", "/api/v1/exam/paper/publish"),
        ("POST", "/api/v1/exam/paper/close"),
        ("GET", "/api/v1/exam/answer/paper/list"),
        ("GET", "/api/v1/exam/answer/paper/get"),
        ("POST", "/api/v1/exam/attempt/start"),
        ("POST", "/api/v1/exam/attempt/save"),
        ("POST", "/api/v1/exam/attempt/submit"),
        ("GET", "/api/v1/exam/attempt/my_list"),
        ("GET", "/api/v1/exam/attempt/my_get"),
        ("GET", "/api/v1/exam/practice/bank/list"),
        ("GET", "/api/v1/exam/practice/question/list"),
        ("POST", "/api/v1/exam/practice/start"),
        ("GET", "/api/v1/exam/practice/get"),
        ("GET", "/api/v1/exam/practice/my_list"),
        ("POST", "/api/v1/exam/practice/answer"),
        ("POST", "/api/v1/exam/practice/finish"),
        ("POST", "/api/v1/exam/practice/retry"),
        ("DELETE", "/api/v1/exam/practice/delete"),
        ("GET", "/api/v1/exam/grading/list"),
        ("GET", "/api/v1/exam/grading/get"),
        ("POST", "/api/v1/exam/grading/claim"),
        ("POST", "/api/v1/exam/grading/release"),
        ("POST", "/api/v1/exam/grading/score"),
        ("POST", "/api/v1/exam/grading/complete"),
    ]
    for method, path in required_apis:
        exists = await Api.filter(tags="答题模块", method=method, path=path).exists()
        if not exists:
            await api_controller.refresh_api()
            break


async def bind_exam_roles():
    root_menu = await Menu.filter(path="/exam", parent_id=0).first()
    if not root_menu:
        return

    exam_menus = await Menu.filter(Q(id=root_menu.id) | Q(parent_id=root_menu.id)).all()
    exam_menu_map = {menu.path: menu for menu in exam_menus}
    exam_apis = await Api.filter(path__startswith="/api/v1/exam/").all()

    admin_role = await Role.filter(name="管理员").first()
    if admin_role:
        current_menu_ids = {menu.id for menu in await admin_role.menus}
        for menu in exam_menus:
            if menu.id not in current_menu_ids:
                await admin_role.menus.add(menu)

        current_api_keys = {(api.method, api.path) for api in await admin_role.apis}
        for api in exam_apis:
            if (api.method, api.path) not in current_api_keys:
                await admin_role.apis.add(api)

    user_role = await Role.filter(name="普通用户").first()
    if not user_role:
        return

    keep_menus = [menu for menu in await user_role.menus if menu.path != "/exam" and menu.parent_id != root_menu.id]
    await user_role.menus.clear()
    for menu in keep_menus:
        await user_role.menus.add(menu)

    for menu in [root_menu, exam_menu_map.get("answer"), exam_menu_map.get("practice")]:
        if menu:
            await user_role.menus.add(menu)

    keep_apis = [api for api in await user_role.apis if not api.path.startswith("/api/v1/exam/")]
    await user_role.apis.clear()
    for api in keep_apis:
        await user_role.apis.add(api)

    allowed_paths = {
        ("GET", "/api/v1/exam/dashboard"),
        ("GET", "/api/v1/exam/answer/paper/list"),
        ("GET", "/api/v1/exam/answer/paper/get"),
        ("POST", "/api/v1/exam/attempt/start"),
        ("POST", "/api/v1/exam/attempt/save"),
        ("POST", "/api/v1/exam/attempt/submit"),
        ("GET", "/api/v1/exam/attempt/my_list"),
        ("GET", "/api/v1/exam/attempt/my_get"),
        ("GET", "/api/v1/exam/practice/bank/list"),
        ("GET", "/api/v1/exam/practice/question/list"),
        ("POST", "/api/v1/exam/practice/start"),
        ("GET", "/api/v1/exam/practice/get"),
        ("GET", "/api/v1/exam/practice/my_list"),
        ("POST", "/api/v1/exam/practice/answer"),
        ("POST", "/api/v1/exam/practice/finish"),
        ("POST", "/api/v1/exam/practice/retry"),
        ("DELETE", "/api/v1/exam/practice/delete"),
    }
    for api in exam_apis:
        if (api.method, api.path) in allowed_paths:
            await user_role.apis.add(api)


async def init_exam_data():
    await init_exam_menus()
    await init_exam_apis()
    await bind_exam_roles()
