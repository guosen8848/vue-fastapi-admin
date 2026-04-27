# 基础版知识库设计说明

本文用于定义 `vue-fastapi-admin` 中“基础版知识库”模块的第一期实现方案，目标是在保持现有管理后台风格不变的前提下，补齐一个可配置、可查询、可发布的知识内容管理能力。

## 1. 目标与范围

### 1.1 目标

- 在现有后台中新增一个标准业务模块“知识库管理”
- 支持知识分类管理与知识文章管理
- 保持当前项目的页面风格、权限模型、动态菜单机制不变
- 采用当前项目已存在的 CRUD 开发模式，减少额外技术引入

### 1.2 本期范围

本期只做“基础版知识库”，不涉及 AI 能力，不做向量检索，不做问答。

本期包含：

- 知识分类的增删改查
- 知识文章的增删改查
- 按标题、分类、状态进行查询
- 文章发布状态管理
- 文章置顶能力
- RBAC 菜单权限与接口权限接入

### 1.3 本期不包含

- 富文本编辑器
- 文件上传、附件管理、图片管理
- 全文检索引擎
- 评论、点赞、收藏
- 版本历史、回收站
- AI 问答、文档切片、向量库

说明：

- 文章内容第一期直接使用纯文本或 Markdown 文本保存
- 页面仍然以后台管理为主，不额外做前台知识门户

## 2. 设计原则

- 尽量复用现有前端 `CrudTable + CrudModal` 模式
- 尽量复用现有后端 `model + schema + controller + api` 分层
- 菜单层级控制在两级以内，适配当前动态路由实现
- 功能先满足录入、维护、查询，再考虑高级编辑体验
- 新增代码尽量集中在新目录中，原有代码只做必要接入

### 2.1 代码隔离要求评估

“在目录下新建一个目录，把新增代码放入里面，原代码尽可能少修改”这个要求是可行的，但无法做到完全零修改。

原因是知识库模块要真正接入现有系统，至少需要完成以下系统级挂载：

- 后端路由注册
- 后端模型注册
- 菜单或初始化数据接入
- 前端页面入口接入动态菜单约定

也就是说：

- 大部分新增业务代码可以集中放在新目录
- 但少量原文件仍需要做“接线式修改”
- 这些修改可以控制在很小范围，尽量只改导入和注册，不改原有业务逻辑

### 2.2 推荐目录方案

后端建议新增一个独立目录：

```text
app/knowledge/
├── __init__.py
├── models.py
├── controllers/
│   ├── __init__.py
│   ├── category.py
│   └── article.py
├── schemas/
│   ├── __init__.py
│   ├── category.py
│   └── article.py
└── api/
    ├── __init__.py
    └── routes.py
```

前端建议新增一个独立目录：

```text
web/src/views/knowledge/
├── category/
│   └── index.vue
└── article/
    └── index.vue
```

前端 API 建议独立文件：

```text
web/src/api/knowledge.js
```

说明：

- 后端业务实现尽量全部放在 `app/knowledge/`
- 前端页面入口必须放在 `web/src/views/knowledge/`，这样才能匹配当前动态路由的组件加载规则
- 如果后续知识库页面内部还要拆子组件，可继续放在 `web/src/views/knowledge/components/`

### 2.3 原代码最小修改范围

为满足现有框架接入，预计只需要少量修改以下原文件：

后端：

- `app/models/__init__.py`
- `app/api/v1/__init__.py`
- `app/core/init_app.py`

前端：

- 原则上可不修改现有页面文件
- `web/src/api/index.js` 可选修改

说明：

- `app/models/__init__.py`：补充新模型导入，让 ORM 和迁移工具识别
- `app/api/v1/__init__.py`：注册知识库路由
- `app/core/init_app.py`：如需自动初始化菜单，则在这里补知识库菜单初始化
- `web/src/api/index.js`：如果坚持统一 API 出口就加导出；若直接在知识库页面中引入 `@/api/knowledge`，则这个文件可以不改

### 2.4 哪些改动可以完全避免

以下原文件通常不需要改：

- `web/src/router/index.js`
- `web/src/store/modules/permission/index.js`
- `web/src/components/table/CrudTable.vue`
- `web/src/composables/useCRUD.js`
- 现有用户、角色、菜单、部门等业务页面

原因：

- 当前项目前端路由是后端动态菜单驱动，不需要手工注册知识库页面路由
- 现有表格、弹窗、CRUD 逻辑可以直接复用
- 知识库模块可以作为一个独立业务块接入，不必侵入已有页面

## 3. 菜单与页面规划

### 3.1 菜单规划

建议新增一个顶级目录菜单：

- 知识库管理

该目录下包含 2 个页面菜单：

- 知识分类
- 知识文章

推荐菜单结构：

```text
知识库管理
├── 知识分类
└── 知识文章
```

推荐路由：

- `/knowledge/category`
- `/knowledge/article`

推荐前端组件路径：

- `/knowledge/category`
- `/knowledge/article`

### 3.2 页面数量

本期共 2 个业务页面：

1. 知识分类页
2. 知识文章页

说明：

- 知识分类新增/编辑使用弹窗
- 知识文章新增/编辑建议使用宽弹窗或抽屉，不单独拆第三个路由页面

### 3.3 页面说明

### 页面一：知识分类

用途：

- 维护知识分类树或一级/二级分类结构

页面能力：

- 分类列表展示
- 新增分类
- 编辑分类
- 删除分类
- 启用/禁用
- 排序

页面形态建议：

- 参考现有“菜单管理”或“部门管理”页面
- 以树形表格或嵌套列表方式展示

### 页面二：知识文章

用途：

- 维护知识库文章内容

页面能力：

- 文章分页列表
- 标题关键字搜索
- 按分类筛选
- 按状态筛选
- 新增文章
- 编辑文章
- 删除文章
- 发布/草稿切换
- 置顶切换

页面形态建议：

- 列表页沿用现有 `CrudTable`
- 编辑区域使用较宽 `CrudModal` 或 `NDrawer`

## 4. 功能设计

### 4.1 知识分类功能

字段建议：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | int | 主键 |
| name | string | 分类名称，唯一 |
| parent_id | int | 父分类 ID，根节点为 0 |
| order | int | 排序 |
| is_active | bool | 是否启用 |
| desc | string | 分类说明，可选 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

规则建议：

- 分类名称全局唯一
- 第一版支持两级分类即可
- 有子分类时不可删除父分类
- 分类下存在文章时不可直接删除，需先迁移或删除文章

### 4.2 知识文章功能

字段建议：

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | int | 主键 |
| title | string | 标题 |
| category_id | int | 所属分类 |
| summary | string | 摘要，可选 |
| content | text | 正文内容 |
| tags | json/string | 标签，第一版可选 |
| status | string | 状态，`draft` / `published` |
| is_top | bool | 是否置顶 |
| published_at | datetime | 发布时间，发布时写入 |
| created_by | int | 创建人 ID，可选 |
| updated_by | int | 更新人 ID，可选 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

规则建议：

- 标题必填
- 分类必选
- 内容必填
- 文章状态默认为 `draft`
- 当状态从 `draft` 切换为 `published` 时写入 `published_at`
- 置顶仅影响后台列表排序，不涉及前台展示

### 4.3 查询与排序

文章列表建议支持：

- 按标题模糊搜索
- 按分类筛选
- 按状态筛选
- 按是否置顶筛选

文章列表排序建议：

1. `is_top` 降序
2. `published_at` 降序
3. `id` 降序

分类列表排序建议：

1. `parent_id` 升序
2. `order` 升序
3. `id` 升序

## 5. 数据模型建议

### 5.1 后端模型

建议新增两个模型：

- `KnowledgeCategory`
- `KnowledgeArticle`

在“新增代码集中到新目录”的约束下，不建议继续把知识库模型放进 `app/models/admin.py`。

更推荐做法是：

- 把知识库模型放在 `app/knowledge/models.py`
- 再在 `app/models/__init__.py` 中做一次导入桥接

这样既能被 ORM 识别，也能减少对原模型文件的侵入。

### 5.2 模型关系

- 一个分类对应多篇文章
- 一篇文章属于一个分类

关系可先使用：

- `KnowledgeArticle.category_id`

第一版不强制引入 ORM 外键联表对象，也可以延续当前项目“显式 ID + 手动补充展示字段”的风格。

## 6. 接口设计建议

### 6.1 路由模块建议

建议新增一个后端模块：

- `app/api/v1/knowledge`

统一前缀：

- `/api/v1/knowledge`

这样便于保持权限字符串一致，也方便在同一模块下管理“分类”和“文章”两组接口。

建议 `tags` 使用：

- `知识库模块`

### 6.2 分类接口

建议接口如下：

- `GET /api/v1/knowledge/category/list`
- `GET /api/v1/knowledge/category/get`
- `POST /api/v1/knowledge/category/create`
- `POST /api/v1/knowledge/category/update`
- `DELETE /api/v1/knowledge/category/delete`

说明：

- `list` 返回树形结构或带 children 的列表
- 风格可参考现有菜单管理接口

### 6.3 文章接口

建议接口如下：

- `GET /api/v1/knowledge/article/list`
- `GET /api/v1/knowledge/article/get`
- `POST /api/v1/knowledge/article/create`
- `POST /api/v1/knowledge/article/update`
- `DELETE /api/v1/knowledge/article/delete`

可选增强：

- `POST /api/v1/knowledge/article/update_status`

说明：

- 第一版即使没有独立 `update_status` 接口，也可直接通过 `update` 完成状态切换

### 6.4 前端 API 方法

建议优先新增独立文件：

- `web/src/api/knowledge.js`

建议在该文件中定义：

- `getKnowledgeCategoryList`
- `getKnowledgeCategoryById`
- `createKnowledgeCategory`
- `updateKnowledgeCategory`
- `deleteKnowledgeCategory`
- `getKnowledgeArticleList`
- `getKnowledgeArticleById`
- `createKnowledgeArticle`
- `updateKnowledgeArticle`
- `deleteKnowledgeArticle`

说明：

- 如果项目后续希望继续保持统一 API 出口，可再选择性地在 `web/src/api/index.js` 中做聚合导出
- 如果目标是“尽量少改原代码”，则知识库页面直接引用 `@/api/knowledge` 即可

## 7. 前端实现建议

### 7.1 页面目录

建议新增：

```text
web/src/views/knowledge/category/index.vue
web/src/views/knowledge/article/index.vue
web/src/api/knowledge.js
```

### 7.2 页面风格

分类页建议复用：

- `CommonPage`
- `CrudTable`
- `CrudModal`

文章页建议复用：

- `CommonPage`
- `CrudTable`
- `CrudModal` 或 `NDrawer`

### 7.3 分类页字段展示建议

表格列建议：

- ID
- 分类名称
- 上级分类
- 排序
- 启用状态
- 创建时间
- 操作

查询栏第一版可以省略，保持简洁。

### 7.4 文章页字段展示建议

表格列建议：

- ID
- 标题
- 分类
- 状态
- 是否置顶
- 更新时间
- 创建时间
- 操作

查询栏建议：

- 标题
- 分类
- 状态

编辑表单建议：

- 标题
- 分类
- 摘要
- 标签
- 内容
- 状态
- 是否置顶

## 8. 权限设计

### 8.1 菜单权限

新增 3 条菜单数据：

1. `知识库管理` 目录菜单
2. `知识分类` 页面菜单
3. `知识文章` 页面菜单

### 8.2 接口权限

知识库模块接口接入现有权限体系后，需通过现有 API 刷新机制同步到 `api` 表，再在角色授权页中分配。

第一版权限粒度按接口控制即可，无需额外设计字段级权限。

### 8.3 按钮权限

前端按钮继续沿用 `v-permission`：

- 分类新增
- 分类编辑
- 分类删除
- 文章新增
- 文章编辑
- 文章删除

## 9. 数据初始化建议

首期建议只初始化菜单，不初始化知识分类与知识文章业务数据。

初始化建议包含：

- 新增“知识库管理”目录菜单
- 新增“知识分类”子菜单
- 新增“知识文章”子菜单

说明：

- 当前项目的默认菜单初始化只在空库首次启动时自动执行
- 已有数据库环境下，建议通过迁移脚本或一次性补数脚本追加菜单数据

## 10. 实现清单

后端：

- 新增知识分类模型
- 新增知识文章模型
- 新增 schema
- 新增 controller
- 新增 `/api/v1/knowledge` 路由模块
- 注册路由
- 生成并执行 Aerich 迁移
- 刷新 API 权限数据
- 补充菜单初始化或补数逻辑

前端：

- 新增知识分类页
- 新增知识文章页
- 新增 API 调用方法
- 配置菜单组件路径
- 接入按钮权限

联调与验证：

- 菜单是否正确显示
- 页面是否能通过动态路由访问
- 接口是否能被角色正确授权
- 分类删除限制是否生效
- 文章查询、发布、置顶是否正常

## 11. 风险与注意事项

- 当前动态菜单实现更适合两级结构，本模块不要继续向下扩三级页面
- 当前项目没有现成富文本编辑器，第一版内容输入体验会偏朴素
- 当前项目没有上传能力页面，本期不要把附件需求纳入实现范围
- 分类删除时要额外检查“是否有子分类”和“是否已被文章引用”
- 已有数据库环境下，菜单初始化不能只依赖首次启动逻辑

## 12. 结论

基础版知识库第一期推荐按“2 个页面 + 2 个模型 + 1 个后端模块”落地：

- 2 个页面：知识分类、知识文章
- 2 个核心实体：分类、文章
- 1 组统一接口前缀：`/api/v1/knowledge/*`

该方案可以最大程度复用当前项目已有的管理后台能力，改动范围明确，复杂度可控，也方便后续逐步扩展附件、Markdown 预览、富文本编辑等能力。
