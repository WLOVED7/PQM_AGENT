# 质量检验知识库 (PQM)

> 多 Agent 系统 — LangGraph + Session 记忆 + Text2SQL + RAG

## 项目背景

**PQM (Product Quality Management)** — 面向制造业的质量检验知识库系统。

核心功能：
- **Text2SQL Agent**: 自然语言转 SQL 查询（客户 → 零件 → 检查项标准/方法/抽检频次）
- **RAG 检索**: 工序异常原因和解决方法检索（热压/喷涂等工序的缺陷处理）
- **多 Agent 协作**: Coordinator + SQL Agent + Critic Agent + RAG

---

## 快速开始

### 1. 克隆项目

```bash
git clone https://github.com/WLOVED7/PQM_AGENT.git
cd PQM_AGENT
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

```bash
cp .env.example .env
# 编辑 .env 填入你的配置
```

### 4. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 5. 访问 API 文档

```
http://localhost:8000/api/v1/docs
```

---

## 环境变量 (.env) 配置说明

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
DB_PASSWORD=你的密码
DB_NAME=pqm_db
DB_CHARSET=utf8mb4

# LLM 配置 (MiniMax)
MiniMax_PROVIDER=minimax
MiniMax_API_KEY=你的API密钥
MiniMax_BASE_URL=https://api.minimaxi.com/anthropic
MiniMax_MODEL=MiniMax-M2.7
MiniMax_MAX_TOKENS=4096
MiniMax_TEMPERATURE=0.7

# RagFlow 配置 (可选，RAG 检索用)
RAGFLOW_BASE_URL=http://localhost:18080
RAGFLOW_API_KEY=你的RagFlow API密钥
RAGFLOW_DATASET_ID=你的数据集ID
```

---

## 依赖

```
fastapi>=0.109.0
uvicorn[standard]>=0.27.0
sqlalchemy>=2.0.25
aiomysql>=0.2.0
pydantic>=2.6.0
pydantic-settings>=2.1.0
httpx>=0.27.0
langgraph>=0.2.0
tqdm>=4.66.0
python-dotenv>=1.0.0
```

---

## 系统架构

```
用户问题
    ↓
┌──────────────────────────────────────────────────────────┐
│                    LangGraph 主图                          │
├──────────────────────────────────────────────────────────┤
│  Coordinator ─── 意图识别 (SQL查询 / RAG检索)              │
│         │                                                 │
│    ┌────┴────┐                                           │
│    ↓         ↓                                           │
│  SQL         RAG                                        │
│    │         │                                           │
│    ↓         ↓                                           │
│  Critic     结果                                         │
│    │                                                 │
│    ↓                                                 │
│  SQL 执行器                                            │
│    ↓                                                 │
│  结果汇总 → 响应优化                                     │
└──────────────────────────────────────────────────────────┘
```

---

## 目录结构

```
PQM/
├── app/
│   ├── main.py                 # FastAPI 入口
│   ├── api/agent.py            # Agent API 端点
│   ├── agents/                 # Agent 节点
│   │   ├── coordinator/        # 意图识别
│   │   ├── sql/                # SQL 生成与执行
│   │   ├── critic/             # SQL 审查
│   │   ├── rag/                # RAG 检索
│   │   └── result/             # 结果汇总
│   ├── tools/                  # 工具
│   │   └── ragflow_client.py   # RagFlow 客户端
│   ├── db/                     # 数据库层
│   ├── state/                  # 状态定义
│   └── memory/                 # 记忆系统
├── data/                       # JSON 示例数据
├── documents/                  # SIP PDF 文档
├── frontend/                   # Vue 前端 (可选)
├── requirements.txt
├── .env.example
└── README.md
```

---

## 数据表结构

| 表名 | 说明 |
|------|------|
| documents | SIP 主表（客户、项目、零件信息） |
| inspection_items | 检验项目表（标准、方法、抽样计划） |
| document_changes | 版本变更记录表 |

---

## API 接口

### Agent 查询

```bash
POST /api/v1/agent/query
{
  "question": "比亚迪前横梁的硬度标准是什么？",
  "session_id": "user-001"
}
```

### 对话历史

```bash
GET /api/v1/agent/history/{session_id}?limit=20
```

### 健康检查

```bash
GET /health
```

---

## 前端 (可选)

前端在 `frontend/` 目录，需要单独安装依赖：

```bash
cd frontend
npm install
npm run dev
```

访问 http://localhost:3000

---

## 前提条件

- Python 3.10+
- MySQL 8.0+
- (可选) RagFlow 服务（用于 RAG 检索）

---

*最后更新: 2026-06-04*