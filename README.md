# 质量检验知识库 (PQM)

> 多 Agent 系统 — LangGraph + Session 记忆 + Text2SQL

## 项目背景

**PQM (Product Quality Management)** — 面向制造业的质量检验知识库系统。

核心功能：
- **Text2SQL Agent**: 自然语言转 SQL 查询
- **RAG 检索**: 文档向量检索（规划中）
- **多 Agent 协作**: Coordinator + SQL Agent + Critic Agent

---

## 系统架构

```
用户问题
    ↓
┌──────────────────────────────────────────────────────────┐
│                    LangGraph 主图                          │
├──────────────────────────────────────────────────────────┤
│                                                          │
│  ┌─────────────┐                                         │
│  │ Coordinator │ ─── 意图识别 (LLM)                        │
│  │  (感知)     │                                         │
│  └──────┬──────┘                                         │
│         │                                                 │
│    ┌────┴────┐                                           │
│    ↓         ↓                                           │
│  SQL         RAG                                         │
│    │         │                                           │
│    ↓         ↓                                           │
│  ┌──────────────┐                                         │
│  │   Critic     │ ─── SQL 审查 + 重试                      │
│  │   (理解)     │                                         │
│  └──────┬──────┘                                         │
│         │                                                 │
│         ↓                                                 │
│  ┌──────────────┐                                         │
│  │ SQL 执行器   │ ─── 执行 SQL                             │
│  │   (执行)     │                                         │
│  └──────┬──────┘                                         │
│         │                                                 │
│         ↓                                                 │
│  ┌──────────────┐                                         │
│  │   结果汇总   │                                         │
│  └──────────────┘                                         │
│                                                          │
└──────────────────────────────────────────────────────────┘
         │
         ↓
┌─────────────────┐
│ Session Memory  │ ←── 记忆系统
│   (记忆)        │
└─────────────────┘
```

### 核心要素

| 要素 | 说明 |
|------|------|
| **感知** | Coordinator Agent 通过 LLM 理解用户问题 |
| **理解** | 意图识别 + Schema 上下文 + 同义词映射 |
| **执行** | SQL 生成 → Critic 审查 → 执行 → 结果汇总 |
| **记忆** | Session 级内存存储，对话历史自动管理 |

---

## 多 Agent 详解

### 1. Coordinator Agent (协调者)

**职责：** 意图识别，决定走 SQL 还是 RAG

- 通过 LLM 分析用户问题
- 识别 DATABASE_QUERY / DOCUMENT_SEARCH / MIXED 意图
- 考虑对话历史上下文中

### 2. SQL Agent (SQL 执行者)

**职责：** 生成并执行 SQL 查询

**子节点：**
- `sql_generation` — 调用 LLM 生成 SQL
- `sql_execution` — 执行 SQL，返回结果

### 3. Critic Agent (审查者)

**职责：** 三层验证 + 重试机制

**验证层次：**
1. **安全校验** — SQL 注入防护（黑名单/白名单）
2. **Schema 校验** — 表/字段是否存在
3. **语义校验** — SQL 能否回答用户问题

**重试逻辑：**
- `needs_regeneration=True` + `retry_count < max` → 重新生成
- `retry_count >= max` → 返回错误

### 4. Session Memory (记忆系统)

**职责：** 管理对话历史

**功能：**
- `add_message()` — 添加消息
- `get_history()` — 获取历史记录
- `get_context_for_llm()` — 生成 LLM 上下文
- `clear_session()` — 清除会话

---

## 目录结构

```
PQM/
├── app/
│   ├── main.py                  # FastAPI 入口
│   │
│   ├── api/
│   │   └── agent.py            # Agent API 端点
│   │
│   ├── graph/                   # LangGraph 核心
│   │   ├── __init__.py
│   │   ├── state.py            # AgentState 定义
│   │   ├── nodes.py            # 节点统一导出
│   │   ├── edges.py            # 边路由逻辑
│   │   └── pqm_graph.py        # LangGraph 主图
│   │
│   ├── agents/
│   │   ├── base/llm.py         # LLM 调用封装
│   │   │
│   │   ├── coordinator/        # Coordinator Agent
│   │   │   ├── __init__.py
│   │   │   ├── coordinator_node.py
│   │   │   └── prompts.py
│   │   │
│   │   ├── sql/                # SQL Agent
│   │   │   ├── __init__.py
│   │   │   ├── sql_generation_node.py
│   │   │   └── sql_execution_node.py
│   │   │
│   │   ├── critic/              # Critic Agent
│   │   │   ├── __init__.py
│   │   │   ├── critic_node.py
│   │   │   └── prompts.py
│   │   │
│   │   ├── rag/                # RAG Agent (待完善)
│   │   │   ├── __init__.py
│   │   │   ├── rag_retrieval_node.py
│   │   │   └── prompts.py
│   │   │
│   │   └── memory/              # Session 记忆系统
│   │       ├── __init__.py
│   │       └── session_memory.py
│   │
│   ├── tools/                   # 工具层
│   │   ├── sql_generator.py    # SQL 生成器
│   │   ├── sql_validator.py    # SQL 安全校验
│   │   ├── sql_executor.py     # SQL 执行器
│   │   └── schema_loader.py    # Schema + 同义词映射
│   │
│   ├── db/                      # 数据库层
│   │   ├── connection.py      # 连接池管理
│   │   └── schema.py           # 表结构定义
│   │
│   └── core/
│       └── config.py           # 配置管理
│
├── data/                        # JSON 示例数据
│   ├── documents.json
│   ├── inspection_items.json
│   └── document_changes.json
│
├── scripts/
│   └── import_data.py          # 数据导入脚本
│
├── alembic/                     # 数据库迁移
│
├── requirements.txt             # 依赖
├── alembic.ini                 # Alembic 配置
└── .env                        # 环境变量
```

---

## AgentState 定义

```python
class AgentState(TypedDict):
    # 用户输入
    question: str
    session_id: str

    # 意图分发
    intent: QueryIntent  # DATABASE_QUERY / DOCUMENT_SEARCH / MIXED
    use_sql: bool
    use_rag: bool

    # SQL 工作流
    generated_sql: Optional[str]
    sql_result: Optional[dict]
    sql_is_valid: bool

    # RAG 工作流
    retrieved_docs: Optional[list]
    rag_result: Optional[str]

    # Critic 反馈
    critic_feedback: Optional[str]
    needs_regeneration: bool

    # 记忆系统
    session_history: Annotated[list[dict], add_messages]

    # 工作流控制
    current_step: WorkflowStep
    retry_count: int
    max_retries: int
```

---

## 数据库表结构

### 三张核心表

| 表名 | 说明 | 关联 |
|------|------|------|
| documents | SIP 主表 | 1 |
| inspection_items | 检验项目表 | N→1 documents |
| document_changes | 版本变更记录表 | N→1 documents |

### 关键字段

**documents:**
- `document_id` — 文档编号【唯一】
- `customer` — 客户名称 (比亚迪/特斯拉)
- `project` — 项目名称
- `part_num` / `part_name` — 零件号/名称
- `version` — 版本号

**inspection_items:**
- `item_id` — 项目编号【唯一】
- `document_id` — 外键 → documents
- `inspection_item` — 检验项目名称
- `requirements` — 检验要求 (JSON)
- `inspection_method` — 检验方法 (JSON)
- `sampling_plan` — 抽样计划 (JSON, 含 AQL)
- `characteristic_level` — 特性等级 (A/B/C)

**document_changes:**
- `change_id` — 变更编号【唯一】
- `document_id` — 外键 → documents
- `version` — 版本号
- `change_date` — 变更日期
- `change_content` — 变更内容

---

## API 接口

### Agent 查询

```
POST /api/v1/agent/query
{
  "question": "前横梁的硬度标准是什么？",
  "session_id": "user-001"
}

响应:
{
  "success": true,
  "question": "前横梁的硬度标准是什么？",
  "intent": "database_query",
  "sql": "SELECT ... FROM inspection_items ...",
  "data": [...],
  "count": 2,
  "error": null
}
```

### 对话历史

```
GET /api/v1/agent/history?session_id=user-001
```

### 健康检查

```
GET /api/v1/agent/health
```

---

## 使用示例

### 1. 启动服务

```bash
cd PQM
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 2. 调用查询

```bash
curl -X POST "http://localhost:8000/api/v1/agent/query" \
  -H "Content-Type: application/json" \
  -d '{"question": "比亚迪项目的SIP有哪些？", "session_id": "test-001"}'
```

### 3. 多轮对话

```bash
# 第一轮
curl -X POST "http://localhost:8000/api/v1/agent/query" \
  -d '{"question": "前横梁的硬度标准是什么？", "session_id": "user-001"}'

# 第二轮 (携带历史记忆)
curl -X POST "http://localhost:8000/api/v1/agent/query" \
  -d '{"question": "那外观检验的标准呢？", "session_id": "user-001"}'
```

---

## 配置说明

### 环境变量 (.env)

```env
# 应用配置
APP_NAME=质量检验知识库
APP_VERSION=1.0.0
DEBUG=false
API_PREFIX=/api/v1

# 数据库配置
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123456
DB_NAME=pqm_db

# LLM 配置
LLM_PROVIDER=anthropic
LLM_API_KEY=your-api-key
LLM_BASE_URL=https://api.minimaxi.com/anthropic
LLM_MODEL=MiniMax-M2.7
LLM_MAX_TOKENS=4096
LLM_TEMPERATURE=0.7
```

---

## 依赖

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.25
aiomysql>=0.2.0
pymysql>=1.1.0
pydantic>=2.6.0
pydantic-settings>=2.1.0
alembic>=1.13.0
tqdm>=4.66.0
python-dotenv>=1.0.0
langgraph>=0.2.0
langchain-anthropic
```

---

## 后续扩展

| 功能 | 状态 | 说明 |
|------|------|------|
| Text2SQL | ✅ 已完成 | LangGraph 多 Agent |
| 意图识别 | ✅ 已完成 | LLM 驱动 |
| Critic 审查 | ✅ 已完成 | 三层验证 + 重试 |
| Session 记忆 | ✅ 已完成 | 内存存储 |
| RAG 检索 | ⏳ 规划中 | 向量 + 全文搜索 |
| 持久化记忆 | ⏳ 规划中 | SQLite/Redis |

---

*文档生成时间: 2026-05-12*