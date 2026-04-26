# vue-fastapi-admin 二次开发文档

本文面向准备在当前项目基础上继续扩展业务模块的开发者，重点说明：

- 项目整体结构
- 本地开发启动方式
- 后端接口、权限、数据初始化机制
- 前端动态路由、菜单、按钮权限机制
- 新增一个业务模块的完整落地步骤
- 常见坑位与排查建议

## 1. 项目概览

这是一个前后端分离的管理后台项目：

- 后端：FastAPI + Tortoise ORM + Aerich
- 前端：Vue 3 + Vite + Pinia + Naive UI
- 鉴权：JWT
- 权限：RBAC（角色 -> 菜单/API）
- 数据库：默认使用 SQLite

项目目录：

```text
.
├── app/                  # 后端代码
├── web/                  # 前端代码
├── deploy/               # Docker / nginx 启动配置
├── run.py                # 后端启动入口
├── pyproject.toml        # Python 依赖与工具配置
├── uv.lock               # uv 锁文件
├── requirements.txt      # pip 兼容依赖文件
└── Makefile              # 常用命令
```

## 2. 本地开发启动

### 2.1 环境要求

- Python 3.11+
- Node.js 18+
- pnpm（推荐）
- uv（推荐）

说明：

- 后端配置默认写在 `app/settings/config.py`，没有额外的 `.env` 依赖
- 默认数据库文件为项目根目录下的 `db.sqlite3`
- 首次启动会自动初始化数据库、迁移、默认管理员、菜单、角色、API 权限数据

### 2.2 后端启动

推荐方式：

```bash
cd /home/guosen/project/vue-fastapi-admin
uv venv --python 3.11
source .venv/bin/activate
uv sync
python run.py
```

兼容方式：

```bash
cd /home/guosen/project/vue-fastapi-admin
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

启动后访问：

- 接口文档：`http://localhost:9999/docs`
- 后端服务：`http://localhost:9999`

### 2.3 前端启动

```bash
cd /home/guosen/project/vue-fastapi-admin/web
pnpm install
pnpm dev
```

启动后访问：

- 前端页面：`http://localhost:3100`

默认登录账号：

- 用户名：`admin`
- 密码：`123456`

### 2.4 常用命令

```bash
make start       # 启动后端
make clean-db    # 清理 sqlite 数据库和 migrations
make migrate     # 生成 Aerich 迁移
make upgrade     # 执行迁移
make lint        # ruff
make format      # black + isort
```

## 3. 后端架构说明

### 3.1 启动流程

后端入口：

- `run.py`
- `app/__init__.py`

启动链路：

1. `python run.py`
2. Uvicorn 加载 `app:app`
3. `app/__init__.py` 中创建 FastAPI 实例
4. 在 `lifespan` 中执行 `init_data()`
5. `init_data()` 依次执行：
   - `init_db()`
   - `init_superuser()`
   - `init_menus()`
   - `init_apis()`
   - `init_roles()`

这意味着：

- 首次启动会自动建库
- 自动生成迁移历史
- 自动创建默认管理员
- 自动生成内置菜单和角色
- 自动把受保护接口同步到 `api` 表

### 3.2 后端目录职责

```text
app/
├── api/          # 路由层
├── controllers/  # 业务逻辑层
├── core/         # 中间件、依赖、异常、初始化
├── models/       # Tortoise ORM 模型
├── schemas/      # Pydantic 请求/响应结构
├── settings/     # 配置
├── utils/        # JWT、密码等工具
└── log/          # 日志
```

各层职责建议：

- `schemas`：定义请求入参和输出结构
- `api`：仅做参数接收、调用 controller、组织响应
- `controllers`：写实际业务逻辑
- `models`：数据库表结构

### 3.3 路由组织方式

接口统一挂在：

- `/api/v1/...`

路由注册入口：

- `app/api/__init__.py`
- `app/api/v1/__init__.py`

现有模块：

- `base`：登录、用户信息、菜单、API 权限
- `user`
- `role`
- `menu`
- `api`
- `dept`
- `auditlog`

每个子模块通常包含两部分：

```text
app/api/v1/<module>/
├── __init__.py   # APIRouter + tags
└── <module>.py   # 接口定义
```

`__init__.py` 中的 `tags` 会被 `refresh_api()` 读入 `api` 表，作为权限模块名称使用。

### 3.4 数据模型

核心表定义在 `app/models/admin.py`：

- `User`
- `Role`
- `Menu`
- `Api`
- `Dept`
- `DeptClosure`
- `AuditLog`

关系大致如下：

- 用户和角色：多对多
- 角色和菜单：多对多
- 角色和 API：多对多
- 部门：树结构，借助 `DeptClosure` 维护层级

如果新增模型，记得在 `app/models/__init__.py` 中导入，否则 Tortoise/Aerich 无法识别。

### 3.5 统一响应格式

封装在 `app/schemas/base.py`：

- `Success`
- `Fail`
- `SuccessExtra`

常见返回格式：

```json
{
  "code": 200,
  "msg": "OK",
  "data": {}
}
```

分页接口格式：

```json
{
  "code": 200,
  "msg": null,
  "data": [],
  "total": 100,
  "page": 1,
  "page_size": 10
}
```

前端 `CrudTable` 默认按这个结构取值。

### 3.6 鉴权与权限

#### 登录

- 登录接口：`POST /api/v1/base/access_token`
- 返回 `access_token`
- 前端后续将 token 放到请求头 `token`

注意：这个项目不是 `Authorization: Bearer xxx`，而是自定义请求头：

```text
token: <jwt>
```

#### 登录校验

定义在 `app/core/dependency.py`：

- `DependAuth`
- `DependPermission`

机制：

- `DependAuth`：校验 token，设置当前用户上下文
- `DependPermission`：校验用户是否拥有当前 `(method, path)` 对应的 API 权限

#### API 权限来源

启动时或手动刷新时，`app/controllers/api.py` 中的 `refresh_api()` 会扫描所有带依赖的接口，将其同步到 `api` 表。

当前逻辑里，只会同步 `route.dependencies` 不为空的接口，所以：

- 需要纳入权限管理的接口，要挂 `DependPermission`
- 至少要带依赖，否则刷新 API 时不会进入权限表

### 3.7 审计日志

中间件定义在 `app/core/middlewares.py`：

- `HttpAuditLogMiddleware`

默认会记录：

- GET
- POST
- PUT
- DELETE

排除路径：

- `/api/v1/base/access_token`
- `/docs`
- `/openapi.json`

如果你新增接口，一般会自动进入审计日志，无需额外处理。

## 4. 前端架构说明

### 4.1 前端启动流程

入口：

- `web/src/main.js`

初始化顺序：

1. 创建 Vue 应用
2. 注册 Pinia
3. 注册动态路由
4. 注册自定义指令
5. 挂载应用

### 4.2 前端目录职责

```text
web/src/
├── api/             # 接口封装
├── assets/          # 静态资源
├── components/      # 通用组件
├── composables/     # 组合式逻辑，如 useCRUD
├── directives/      # 自定义指令，如按钮权限
├── layout/          # 布局
├── router/          # 路由与守卫
├── store/           # Pinia 状态管理
├── styles/          # 样式
├── utils/           # 工具函数、请求封装、token 管理
└── views/           # 页面目录
```

### 4.3 请求与代理

请求封装：

- `web/src/utils/http/index.js`
- `web/src/utils/http/interceptors.js`

特点：

- 默认 `baseURL = /api/v1`
- token 自动放到 `headers.token`
- 后端返回 `code !== 200` 会统一弹消息

开发代理配置：

- `web/.env.development`
- `web/build/constant.js`

开发时：

- 前端：`http://localhost:3100`
- `/api/v1` 代理到：`http://127.0.0.1:9999`

### 4.4 动态菜单与路由

关键文件：

- `web/src/store/modules/permission/index.js`
- `web/src/router/index.js`

动态路由来源：

1. 登录后获取用户信息
2. 请求 `GET /api/v1/base/usermenu`
3. 前端根据后端菜单数据动态生成路由

生成规则：

- 顶级路由组件固定用 `Layout`
- 子页面组件从 `views` 目录动态匹配
- 匹配规则是：

```text
/src/views${menu.component}/index.vue
```

例如：

- 后端菜单 `component = "/system/user"`
- 前端实际页面文件必须存在：
  `web/src/views/system/user/index.vue`

这条规则非常重要，路径不一致时页面会直接加载失败。

### 4.5 按钮权限

权限指令：

- `web/src/directives/permission.js`

判断依据：

- 当前用户可访问 API 列表，来源于 `GET /api/v1/base/userapi`

权限字符串格式：

```text
<method小写><path>
```

例如：

- `get/api/v1/user/list`
- `post/api/v1/user/create`
- `delete/api/v1/menu/delete`

页面里可以这样使用：

```vue
<n-button v-permission="'post/api/v1/order/create'">新增</n-button>
```

或者在 `render` 函数里配合 `withDirectives` 使用。

### 4.6 CRUD 页面开发模式

当前项目已经形成固定模式，建议沿用：

- 页面放在 `web/src/views/...`
- 接口统一放在 `web/src/api/index.js`
- 新增/编辑/删除逻辑复用 `web/src/composables/useCRUD.js`
- 列表组件复用 `web/src/components/table/CrudTable.vue`
- 弹窗复用 `web/src/components/table/CrudModal.vue`

这样做的好处是：

- 代码风格一致
- 页面开发速度快
- 容易和现有模块保持统一体验

## 5. 新增一个业务模块的推荐步骤

下面以“订单模块”为例说明。

### 5.1 后端新增模块

#### 第一步：定义模型

在 `app/models/` 下新增或补充模型，例如：

```python
class Order(BaseModel, TimestampMixin):
    order_no = fields.CharField(max_length=64, unique=True)
    status = fields.CharField(max_length=32)
```

然后在 `app/models/__init__.py` 中导入。

#### 第二步：定义 schema

在 `app/schemas/` 下新增：

- `OrderCreate`
- `OrderUpdate`
- 需要的查询/详情结构

#### 第三步：定义 controller

在 `app/controllers/` 下新增 `order.py`，通常继承 `CRUDBase`：

```python
class OrderController(CRUDBase[Order, OrderCreate, OrderUpdate]):
    def __init__(self):
        super().__init__(model=Order)
```

如有复杂业务逻辑，也放在这里。

#### 第四步：定义 API

新增目录：

```text
app/api/v1/orders/
├── __init__.py
└── orders.py
```

接口建议保持和现有模块一致：

- `GET /list`
- `GET /get`
- `POST /create`
- `POST /update`
- `DELETE /delete`

`__init__.py` 中记得加清晰的 `tags`，如：

```python
orders_router.include_router(router, tags=["订单模块"])
```

#### 第五步：注册路由

在 `app/api/v1/__init__.py` 中注册：

```python
v1_router.include_router(orders_router, prefix="/order", dependencies=[DependPermission])
```

如果需要登录但不做细粒度权限，也至少要考虑依赖策略，因为 API 刷新依赖它识别受保护接口。

#### 第六步：生成迁移

```bash
make migrate
make upgrade
```

或者：

```bash
aerich migrate
aerich upgrade
```

#### 第七步：刷新 API 权限表

启动项目后，可以在系统的 API 管理页点击“刷新 API”，或者直接调用：

- `POST /api/v1/api/refresh`

这样新的受保护接口才会进入权限表。

### 5.2 前端新增页面

#### 第一步：新增页面文件

按后端菜单 `component` 路径创建页面文件。例如：

```text
web/src/views/order/list/index.vue
```

则对应的后端菜单 `component` 应写为：

```text
/order/list
```

#### 第二步：补充接口封装

在 `web/src/api/index.js` 中增加：

```javascript
getOrderList: (params = {}) => request.get('/order/list', { params }),
createOrder: (data = {}) => request.post('/order/create', data),
updateOrder: (data = {}) => request.post('/order/update', data),
deleteOrder: (params = {}) => request.delete('/order/delete', { params }),
```

#### 第三步：参考现有 CRUD 页开发

推荐直接参考：

- `web/src/views/system/user/index.vue`
- `web/src/views/system/role/index.vue`
- `web/src/views/system/menu/index.vue`

开发顺序通常是：

1. 定义查询条件
2. 定义表格列
3. 接入 `CrudTable`
4. 接入 `useCRUD`
5. 增加弹窗表单
6. 给按钮加 `v-permission`

#### 第四步：创建菜单

系统菜单来自数据库，不是前端写死。

可以通过系统“菜单管理”页面新增，也可以自己写初始化逻辑插入菜单数据。

菜单建议：

- 目录：`component = "Layout"`
- 具体页面：`component = "/xxx/yyy"`

例如：

- 一级目录：`/order`，`component = "Layout"`
- 二级菜单：`path = "list"`，`component = "/order/list"`

#### 第五步：给角色授权

新增完菜单和 API 后，需要在“角色管理”里把：

- 菜单权限
- API 权限

分配给对应角色，否则普通用户看不到页面或无法调用接口。

## 6. 数据库与迁移

### 6.1 默认数据库

默认配置在 `app/settings/config.py`：

- 使用 SQLite
- 文件位置：`<项目根目录>/db.sqlite3`

如需切换 MySQL/PostgreSQL，可直接修改 `TORTOISE_ORM` 配置，并安装对应驱动。

### 6.2 Aerich 使用要点

配置来自 `pyproject.toml`：

```toml
[tool.aerich]
tortoise_orm = "app.settings.TORTOISE_ORM"
location = "./migrations"
src_folder = "./."
```

新增/修改模型后推荐流程：

1. 改模型
2. 确认 `app/models/__init__.py` 已导入
3. 执行 `aerich migrate`
4. 执行 `aerich upgrade`

如果只是本地临时试验，也可以清库重建：

```bash
make clean-db
python run.py
```

## 7. 常见坑位

### 7.1 菜单能创建，但页面打不开

优先检查后端菜单的 `component` 字段是否能映射到实际文件：

```text
/src/views${component}/index.vue
```

例如：

- `component = "/system/user"`
- 文件必须是 `web/src/views/system/user/index.vue`

### 7.2 普通用户能看到按钮，但点击 403

通常有两种原因：

1. 角色没有分配对应 API 权限
2. 按钮没有加 `v-permission`

### 7.3 新增接口后，角色授权里看不到

检查：

1. 路由是否注册到了 `app/api/v1/__init__.py`
2. 是否加了依赖，尤其是 `DependPermission`
3. 是否执行过 API 刷新

### 7.4 菜单层级过深

当前 `GET /api/v1/base/usermenu` 的组装逻辑是“顶级菜单 + 直接子菜单”，适合两级菜单结构。

建议二次开发时优先保持：

- 一级目录
- 二级业务页

不要默认按无限层级去设计菜单。

### 7.5 按钮权限字符串写错

按钮权限不是菜单名，也不是接口名，而是：

```text
请求方法小写 + 接口完整 path
```

例如：

```text
post/api/v1/user/create
```

### 7.6 接口认证头写错

当前项目使用：

```text
token: <jwt>
```

不是：

```text
Authorization: Bearer <jwt>
```

### 7.7 前端代理不生效

确认：

- 前端是通过 `pnpm dev` 启动
- 请求路径以 `/api/v1` 开头
- 后端运行在 `127.0.0.1:9999`

## 8. 建议的二次开发约定

为了让后续模块更好维护，建议统一遵循以下约定：

1. 后端接口命名尽量与现有模块保持一致：`list/get/create/update/delete`
2. 业务逻辑尽量放在 `controllers`，不要把复杂代码堆在路由层
3. 前端列表页优先复用 `CrudTable` + `useCRUD`
4. 菜单尽量保持两级
5. 受保护接口统一纳入 API 权限表
6. 页面按钮统一补 `v-permission`
7. 数据模型变更后及时补迁移

## 9. 现阶段可继续补强的方向

当前项目已经适合做中小型后台二次开发，但如果要长期维护，建议逐步补齐：

- 自动化测试
- 区分开发/生产配置
- 更标准的认证头方案
- 更明确的服务层/领域层边界
- 更完整的数据初始化脚本
- 更严格的异常码和错误响应规范

---

如果后续你准备开始加具体业务模块，建议先按“模型 -> schema -> controller -> API -> 前端页面 -> 菜单 -> 角色授权”这个顺序推进，基本不会乱。
