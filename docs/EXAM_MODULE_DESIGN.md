# 答题模块设计说明

本文用于定义 `vue-fastapi-admin` 中“答题模块”的第一期实现方案，目标是在现有后台风格和 RBAC 机制不变的前提下，补齐题库导入、选题组卷、答题提交、自动判题与人工阅卷能力。

## 1. 目标与范围

### 1.1 目标

- 支持上传指定格式的题库文件，并完成结构校验与批量导入
- 支持从题库中筛选并选出题目，生成试卷
- 支持用户在线答题与提交
- 仅对选择题自动判分，其余题型进入人工阅卷
- 保持当前项目的 `model + schema + controller + api + view` 分层方式
- 接入现有菜单、API 权限和动态路由体系

### 1.2 第一期范围

第一期建议覆盖以下能力：

- 题库导入
- 题目管理
- 试卷管理
- 在线答题
- 选择题自动判题
- 填空题/简答题人工判题
- 成绩汇总与答题记录查看

### 1.3 第一期不包含

第一期建议暂不做以下内容：

- 随机抽题策略
- AI 阅卷
- 判断题自动判题扩展
- 多次考试机会配置
- 防作弊、切屏检测、摄像头监考
- Word/PDF 题库直接解析
- 主观题关键字半自动判分
- 复杂题型（材料题、组合题、编程题）

说明：

- 第一期优先把流程打通，不追求一次把所有题型做全
- 题型先聚焦 `单选题 / 多选题 / 填空题 / 简答题`
- “选择题自动判，其余题目手动判”严格按需求执行，不额外引入模糊判分逻辑

## 2. 设计原则

- 尽量复用现有前端 `CrudTable + CrudModal` 交互模式
- 尽量复用现有后端 `CRUDBase` 和独立业务目录的组织方式
- 题库导入采用“模板驱动 + 严格校验”，避免脏数据进入系统
- 试卷保存时冻结题目快照，避免后续改题影响历史答题记录
- 自动判题和人工判题分阶段处理，状态要明确可追踪
- 新增代码尽量集中到单独目录，原文件只做必要注册和接线

## 3. 推荐目录方案

### 3.1 后端目录

建议新增独立模块：

```text
app/exam/
├── __init__.py
├── constants.py
├── models.py
├── init.py
├── controllers/
│   ├── __init__.py
│   ├── bank.py
│   ├── question.py
│   ├── paper.py
│   ├── attempt.py
│   └── grading.py
├── schemas/
│   ├── __init__.py
│   ├── bank.py
│   ├── question.py
│   ├── paper.py
│   ├── attempt.py
│   └── grading.py
└── api/
    ├── __init__.py
    └── routes.py
```

### 3.2 前端目录

```text
web/src/views/exam/
├── bank/
│   └── index.vue
├── question/
│   └── index.vue
├── paper/
│   └── index.vue
├── grading/
│   └── index.vue
└── answer/
    └── index.vue
```

前端 API 建议独立文件：

```text
web/src/api/exam.js
```

### 3.3 原代码最小修改范围

预计只需要少量修改以下原文件：

- `app/models/__init__.py`
- `app/api/v1/__init__.py`
- `app/core/init_app.py`
- `web/src/api/index.js`（可选）

如果要自动初始化菜单和 API，还需要新增：

- `app/exam/init.py`

说明：

- 这一点与当前知识库模块接入方式保持一致
- 题库文件上传可以参考知识库模块的“上传临时文件 -> 校验通过后再落业务数据”的实现思路

## 4. 菜单与角色规划

### 4.1 菜单规划

建议新增一个顶级目录菜单：

- 答题管理

目录下建议包含 4 个页面：

- 题库管理
- 题目管理
- 试卷管理
- 阅卷中心

如果第一期就需要完整答题入口，可再增加：

- 我的答题

推荐路由：

- `/exam/bank`
- `/exam/question`
- `/exam/paper`
- `/exam/grading`
- `/exam/answer`

### 4.2 角色建议

建议按职责拆成以下角色：

- 题库管理员：导入题库、维护题目
- 组卷管理员：选择题目、配置试卷
- 阅卷人：处理人工判题
- 答题人：查看可用试卷并提交答案

说明：

- 第一阶段也可以先只用管理员角色打通功能
- 后续再通过菜单和 API 权限拆到更细粒度角色

## 5. 功能设计

### 5.1 题库导入

#### 5.1.1 导入方式

第一期建议只支持 `xlsx` 模板导入。

原因：

- 运营和教务类用户更容易维护 Excel
- 后端用 `openpyxl` 即可解析，依赖轻
- 比直接解析 Word/PDF 稳定很多

导入页面建议由两部分组成：

- 题库基础信息：题库名称、说明、状态
- 模板文件上传：上传 `xlsx` 文件并执行校验

#### 5.1.2 模板格式

建议固定一个 Sheet，名称为：

- `questions`

建议模板表头如下：

| 列名 | 必填 | 说明 | 示例 |
| --- | --- | --- | --- |
| 题型 | 是 | `单选题 / 多选题 / 填空题 / 简答题` | 单选题 |
| 题目分类 | 否 | 分类路径，使用 `/` 分隔 | Python/基础 |
| 题干 | 是 | 题目正文 | Python 中列表使用哪个关键字定义？ |
| 选项A | 选择题必填 | 选项内容 | list |
| 选项B | 选择题必填 | 选项内容 | dict |
| 选项C | 否 | 选项内容 | tuple |
| 选项D | 否 | 选项内容 | set |
| 选项E | 否 | 选项内容 | 预留 |
| 选项F | 否 | 选项内容 | 预留 |
| 正确答案 | 选择题必填 | 单选填 `A`，多选支持 `A,C` 或 `AC` | A |
| 分值 | 是 | 正整数或一位小数 | 5 |
| 难度 | 否 | `简单 / 中等 / 困难` | 简单 |
| 解析 | 否 | 题目解析 | 列表使用方括号定义 |
| 参考答案 | 否 | 填空题/简答题参考答案 | 用于人工阅卷参考 |
| 标签 | 否 | 多个标签用逗号分隔 | Python,基础 |

#### 5.1.3 模板规则

- 每一行代表一道题
- 选择题至少要有 2 个有效选项
- 单选题 `正确答案` 只能有 1 个值
- 多选题 `正确答案` 支持英文逗号分隔或紧凑写法，如 `A,C`、`AC`，提交后统一转成大写数组
- 填空题和简答题可以不填 `正确答案`，但建议填写 `参考答案`
- 空行自动跳过
- 题干去首尾空格后不能为空
- 同一题库内如果题干完全重复，默认视为重复题并阻止导入

#### 5.1.4 示例

| 题型 | 题目分类 | 题干 | 选项A | 选项B | 选项C | 选项D | 正确答案 | 分值 | 难度 | 解析 | 参考答案 | 标签 |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| 单选题 | Python/基础 | Python 中列表使用哪个符号定义？ | `[]` | `{}` | `()` | `<>` | A | 5 | 简单 | 列表使用方括号定义 |  | Python,列表 |
| 多选题 | FastAPI/基础 | 以下哪些属于常见 HTTP 方法？ | GET | POST | INPUT | DELETE | A,B,D | 10 | 简单 | GET/POST/DELETE 都是合法方法 |  | FastAPI,HTTP |
| 填空题 | SQL/基础 | 请写出查询全部字段的 SQL 语句。 |  |  |  |  |  | 5 | 简单 |  | `SELECT * FROM table_name;` | SQL |
| 简答题 | 架构/设计 | 请说明为什么要保存试卷题目快照。 |  |  |  |  |  | 15 | 中等 |  | 防止原题修改后影响历史答题记录 | 设计 |

#### 5.1.5 导入校验流程

建议流程如下：

1. 上传原始 `xlsx`
2. 校验文件扩展名、大小、Sheet 名称、表头完整性
3. 逐行解析并生成结构化题目数据
4. 返回错误明细预览
5. 校验全部通过后，再写入数据库
6. 保存导入批次信息和原始文件路径

导入失败时建议返回：

- 错误总数
- 行号
- 字段名
- 错误原因

例如：

- 第 12 行：题型为单选题，但未填写正确答案
- 第 18 行：正确答案 `A,E` 超出已有选项范围
- 第 25 行：题干重复

### 5.2 题目管理

题目管理页建议支持：

- 按题库筛选
- 按题型筛选
- 按题目分类筛选
- 按关键字检索题干
- 按难度筛选
- 查看题目详情
- 手工新增题目
- 编辑题目
- 禁用题目

删除策略建议：

- 如果题目从未被试卷引用，可物理删除
- 如果题目已经被试卷引用，建议只允许“禁用”，不建议物理删除

说明：

- 由于试卷会保存题目快照，所以即使后续编辑题库题目，也不会影响已组好的试卷和历史答卷

### 5.3 试卷管理

试卷管理页建议支持：

- 创建试卷
- 从题库中筛选并勾选题目
- 批量加入试卷
- 调整题目顺序
- 修改每道题在当前试卷中的分值
- 计算试卷总分
- 发布/关闭试卷

试卷状态建议：

- `draft`：草稿
- `published`：已发布，可答题
- `closed`：已关闭，不可再答题

组卷规则建议：

- 同一道题在同一试卷中不能重复出现
- 题目加入试卷时，默认带出题库中的默认分值
- 允许组卷人对当前试卷单独调整分值
- 保存试卷时写入 `question_snapshot`，至少包含：
  - 题型
  - 题干
  - 选项
  - 正确答案
  - 参考答案
  - 解析
  - 标签

#### 5.3.1 试卷创建示例

```json
{
  "title": "Python 基础测试卷",
  "desc": "用于新员工入门测试",
  "pass_score": 60,
  "duration_minutes": 30,
  "status": "draft",
  "questions": [
    { "question_id": 101, "score": 5, "sort_order": 1 },
    { "question_id": 102, "score": 10, "sort_order": 2 },
    { "question_id": 205, "score": 15, "sort_order": 3 }
  ]
}
```

### 5.4 在线答题

第一期建议支持最小可用闭环：

- 查看可答试卷列表
- 进入试卷答题页
- 暂存答案
- 提交答案
- 查看自己的作答结果和判题状态

答题限制建议：

- 第一版默认一个用户对同一试卷只允许提交 1 次
- 试卷关闭后不可再开始新答卷
- 已提交答卷不可修改

答案格式建议：

- 单选题：`["A"]`
- 多选题：`["A", "C"]`
- 填空题：`"SELECT * FROM user;"`
- 简答题：长文本字符串

### 5.5 自动判题

自动判题范围仅包含：

- 单选题
- 多选题

判题规则建议：

#### 单选题

- 用户答案与标准答案完全一致则满分
- 否则 0 分

#### 多选题

- 先统一转大写、去空格、排序后比较
- 只有答案集合完全一致才得满分
- 第一版不做部分得分

说明：

- 这种规则实现简单、结果稳定，适合先落地
- 如果后续要做多选题部分得分，可以在第二期单独扩展

### 5.6 人工判题

人工判题范围：

- 填空题
- 简答题

处理方式建议：

- 用户提交后，系统先完成选择题自动判分
- 如果答卷中存在人工题，则答卷状态变为 `pending_review`
- 阅卷人在“阅卷中心”按题逐项给分
- 所有人工题判完后，系统汇总最终成绩并把答卷状态改为 `graded`

阅卷页建议展示：

- 试卷信息
- 答题人信息
- 自动判分结果
- 人工题题干
- 用户答案
- 参考答案
- 本题满分
- 当前给分
- 阅卷备注

人工判题规则建议：

- 每题给分范围 `0 <= score <= 本题分值`
- 支持填写评语
- 所有人工题必须判完才允许完成阅卷

### 5.7 成绩与状态流转

答卷状态建议：

- `in_progress`：答题中
- `submitted`：已提交，等待系统处理
- `pending_review`：已完成自动判题，等待人工阅卷
- `graded`：阅卷完成

单题判题状态建议：

- `auto_correct`：自动判题且正确
- `auto_wrong`：自动判题且错误
- `manual_pending`：待人工判题
- `manual_done`：人工判题完成

状态流转建议：

```text
开始答题 -> in_progress
提交答卷 -> submitted
仅含选择题 -> graded
含人工题 -> pending_review
阅卷完成 -> graded
```

## 6. 数据模型设计

### 6.1 `ExamBank` 题库表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| name | varchar(100) | 题库名称 |
| desc | varchar(500) | 题库说明 |
| source_file_name | varchar(255) | 原始文件名 |
| source_file_path | varchar(500) | 原始文件存储路径 |
| question_count | int | 题目数量 |
| is_active | bool | 是否启用 |
| created_by | int | 创建人 |
| updated_by | int | 更新人 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 6.2 `ExamQuestion` 题目表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| bank_id | bigint | 所属题库 |
| question_type | varchar(32) | 题型 |
| category_path | varchar(255) | 分类路径 |
| stem | text | 题干 |
| correct_answer | json | 标准答案 |
| reference_answer | text | 主观题参考答案 |
| analysis | text | 解析 |
| tags | json | 标签 |
| difficulty | varchar(16) | 难度 |
| default_score | decimal(6,2) | 默认分值 |
| is_active | bool | 是否启用 |
| created_by | int | 创建人 |
| updated_by | int | 更新人 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- `correct_answer` 推荐统一存 JSON
- 单选题存 `["A"]`
- 多选题存 `["A", "C"]`
- 主观题可以为空

### 6.3 `ExamQuestionOption` 题目选项表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| question_id | bigint | 题目 ID |
| option_key | varchar(4) | 选项键，如 `A` |
| option_content | text | 选项内容 |
| sort_order | int | 排序 |

### 6.4 `ExamPaper` 试卷表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| title | varchar(200) | 试卷标题 |
| desc | varchar(500) | 试卷说明 |
| status | varchar(32) | 试卷状态 |
| duration_minutes | int | 限时分钟数 |
| pass_score | decimal(6,2) | 及格分 |
| total_score | decimal(6,2) | 总分 |
| question_count | int | 题目数量 |
| is_active | bool | 是否启用 |
| created_by | int | 创建人 |
| updated_by | int | 更新人 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 6.5 `ExamPaperQuestion` 试卷题目关联表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| paper_id | bigint | 试卷 ID |
| question_id | bigint | 来源题目 ID |
| sort_order | int | 题目顺序 |
| score | decimal(6,2) | 本试卷中的实际分值 |
| question_snapshot | json | 题目快照 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

说明：

- `question_snapshot` 是这个模块的关键字段
- 历史答卷、阅卷、成绩查询都应基于快照，而不是实时回查原题

### 6.6 `ExamAttempt` 答卷表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| paper_id | bigint | 试卷 ID |
| user_id | bigint | 答题人 |
| status | varchar(32) | 答卷状态 |
| objective_score | decimal(6,2) | 选择题自动得分 |
| subjective_score | decimal(6,2) | 人工题得分 |
| total_score | decimal(6,2) | 总分 |
| started_at | datetime | 开始时间 |
| submitted_at | datetime | 提交时间 |
| graded_at | datetime | 阅卷完成时间 |
| graded_by | int | 阅卷人 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

### 6.7 `ExamAnswer` 单题作答表

| 字段 | 类型 | 说明 |
| --- | --- | --- |
| id | bigint | 主键 |
| attempt_id | bigint | 答卷 ID |
| paper_question_id | bigint | 试卷题目关联 ID |
| question_id | bigint | 原题 ID |
| question_type | varchar(32) | 题型 |
| answer_payload | json | 用户答案 |
| judge_status | varchar(32) | 判题状态 |
| is_correct | bool | 自动判题结果 |
| auto_score | decimal(6,2) | 自动得分 |
| manual_score | decimal(6,2) | 人工得分 |
| final_score | decimal(6,2) | 最终得分 |
| reviewer_comment | text | 阅卷备注 |
| answer_snapshot | json | 答题时题目快照 |
| judged_at | datetime | 判题时间 |
| judged_by | int | 判题人 |
| created_at | datetime | 创建时间 |
| updated_at | datetime | 更新时间 |

## 7. 接口设计

接口风格建议延续当前项目习惯，返回结构使用现有：

- `Success`
- `SuccessExtra`
- `Fail`

### 7.1 题库接口

- `GET /api/v1/exam/bank/list`
- `GET /api/v1/exam/bank/get`
- `POST /api/v1/exam/bank/create`
- `POST /api/v1/exam/bank/update`
- `DELETE /api/v1/exam/bank/delete`
- `POST /api/v1/exam/bank/import`
- `GET /api/v1/exam/bank/template`

说明：

- `template` 用于下载标准导入模板
- `import` 负责文件接收、校验和落库

### 7.2 题目接口

- `GET /api/v1/exam/question/list`
- `GET /api/v1/exam/question/get`
- `POST /api/v1/exam/question/create`
- `POST /api/v1/exam/question/update`
- `DELETE /api/v1/exam/question/delete`

### 7.3 试卷接口

- `GET /api/v1/exam/paper/list`
- `GET /api/v1/exam/paper/get`
- `POST /api/v1/exam/paper/create`
- `POST /api/v1/exam/paper/update`
- `DELETE /api/v1/exam/paper/delete`
- `POST /api/v1/exam/paper/publish`
- `POST /api/v1/exam/paper/close`

### 7.4 答题接口

- `GET /api/v1/exam/answer/paper/list`
- `GET /api/v1/exam/answer/paper/get`
- `POST /api/v1/exam/attempt/start`
- `POST /api/v1/exam/attempt/save`
- `POST /api/v1/exam/attempt/submit`
- `GET /api/v1/exam/attempt/my_list`
- `GET /api/v1/exam/attempt/my_get`

### 7.5 阅卷接口

- `GET /api/v1/exam/grading/list`
- `GET /api/v1/exam/grading/get`
- `POST /api/v1/exam/grading/score`
- `POST /api/v1/exam/grading/complete`

## 8. 关键流程

### 8.1 题库导入流程

```text
上传模板文件
-> 服务端校验文件与表头
-> 逐行解析题目
-> 返回错误或导入成功
-> 写入题库、题目、选项数据
```

### 8.2 组卷流程

```text
创建试卷
-> 按题库/题型/分类筛选题目
-> 勾选题目加入试卷
-> 调整顺序和分值
-> 保存题目快照
-> 发布试卷
```

### 8.3 判题流程

```text
用户提交答卷
-> 系统自动判选择题
-> 如仅含选择题，直接生成最终成绩
-> 如含主观题，进入待阅卷
-> 阅卷人逐题给分
-> 汇总最终成绩
```

## 9. 前端页面建议

### 9.1 题库管理页

- 列表查看题库
- 上传题库模板
- 查看导入结果
- 查看题目数量

### 9.2 题目管理页

- 列表查询题目
- 查看题目详情和选项
- 新增/编辑/禁用题目

### 9.3 试卷管理页

- 创建试卷基本信息
- 侧边弹窗选择题目
- 预览题目顺序与总分

### 9.4 阅卷中心

- 按试卷、答题人、状态筛选
- 左侧题号导航
- 右侧单题阅卷区
- 完成阅卷后回写总分

### 9.5 我的答题

- 展示可答试卷
- 进入答题页
- 支持暂存和提交
- 查看成绩与阅卷状态

## 10. 实施顺序建议

建议按以下顺序推进：

### 第一步：后端题库与题目基础能力

- 新增模型、枚举、schema
- 完成题库导入
- 完成题目 CRUD

### 第二步：试卷管理

- 完成试卷与试卷题目关联
- 完成选题组卷和题目快照

### 第三步：答题与自动判题

- 完成开始答题、暂存、提交
- 完成选择题自动判题

### 第四步：人工阅卷

- 完成阅卷列表、详情、评分、完成阅卷

### 第五步：菜单与权限接入

- 注册路由
- 刷新 API
- 初始化菜单
- 配置角色权限

## 11. 技术建议

- Excel 解析建议使用 `openpyxl`
- 题库文件存储建议复用当前 `storage/` 目录模式
- 导入、组卷、提交答卷都建议使用事务
- 多选题答案建议统一标准化为大写数组后再存储
- 快照字段建议使用 JSON，避免后续频繁 join 和历史数据漂移

## 12. 本期关键决策

- 第一版只支持 `xlsx` 模板导入
- 第一版只对单选题、多选题自动判分
- 第一版多选题必须全对才给分，不做部分分
- 第一版填空题、简答题全部人工阅卷
- 第一版默认每个用户每张试卷只允许提交一次
- 第一版答题页可以先放在当前后台体系内，不额外拆独立门户

## 13. 后续可扩展方向

- 判断题自动判题
- 题库分类独立管理
- 随机抽题规则
- 错题本
- 成绩统计报表
- 主观题关键词辅助判分
- AI 阅卷建议

---

如果按这个方案推进，后续开发建议先从“题库导入 + 题目管理”开始，这部分最稳定，也最容易先形成可验证成果。
