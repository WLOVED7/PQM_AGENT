# 质量检验知识库 (PQM)

> FastAPI + SQLAlchemy 2.0 (异步) + MySQL 8 质量检验文档管理系统

[![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-green.svg)](https://fastapi.tiangolo.com/)

## 项目背景

### 什么是 SIP？

SIP = **Standard Inspection Procedure** (标准检验规程)

制造业在生产零件时，需要按照标准文件对零件进行检验。这个标准文件就是 SIP。

### 一个 SIP 文档的例子：

```json
{
  "document_id": "VHST-SIP-SA2HG-014",
  "customer": "比亚迪",
  "project": "SA2HG",
  "part_num": "SA2HG-5101311",
  "part_name": "前横梁",
  "document_type": "SIP",
  "version": "A/6",
  "drawing_version": "B/0",
  "mold_num": "MH-12345",
  "prepared_date": "2024-01-15",
  "status": "active"
}
```

检验项目：
- 外观检验 - 不允许有生锈、开裂、压伤
- 尺寸检验 - 长度500±0.5mm
- 硬度检验 - HRC 45-55
- 材料成分检验 - 碳含量0.15%-0.25%

### 系统解决什么问题？

| 问题 | 解决方案 |
|------|----------|
| 纸质文档难管理 | 数字化存储到 MySQL |
| 查询不方便 | 提供 REST API 接口 |
| Agent 无法理解数据 | 标准化 schema + chunk_text |
| 自然语言查询 | 支持 Text2SQL |
| 全文搜索 | MySQL FULLTEXT 索引 |

---

## 系统架构

```
┌─────────────────────────────────────────────────────────────────┐
│                        质量检验知识库                              │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐    ┌──────────┐    ┌──────────┐                   │
│  │  JSON    │    │  FastAPI │    │  MySQL   │                   │
│  │  数据    │───▶│   API    │───▶│  数据库   │                   │
│  └──────────┘    └──────────┘    └──────────┘                   │
│       │               │               │                         │
│       ▼               ▼               ▼                         │
│  import_data.py   CRUD API      3张核心表                        │
│                       │         ┌─────────────┐                  │
│                       └────────▶│ documents   │ ← SIP主表        │
│                                 ├─────────────┤                  │
│                                 │inspection_  │ ← 检验项目       │
│                                 │  items      │                  │
│                                 ├─────────────┤                  │
│                                 │document_    │ ← 版本变更       │
│                                 │ changes     │                  │
│                                 └─────────────┘                  │
└─────────────────────────────────────────────────────────────────┘

未来扩展：
                              ┌──────────┐
                              │  Agent   │ ← Text2SQL 自然语言查询
                              └──────────┘
                              ┌──────────┐
                              │   RAG    │ ← 向量检索
                              └──────────┘
```

---

## 项目结构

```
PQM/
├── app/
│   ├── api/              # FastAPI 路由 (接口定义)
│   │   ├── documents.py       # 文档管理接口
│   │   ├── inspection_items.py # 检验项目管理接口
│   │   └── document_changes.py # 变更记录接口
│   │
│   ├── models/           # SQLAlchemy ORM 模型 (数据库表结构)
│   │
│   ├── schemas/          # Pydantic 模型 (API 数据验证)
│   │
│   ├── crud/             # CRUD 操作 (数据库读写)
│   │
│   ├── services/         # 业务逻辑层
│   │
│   ├── core/             # 核心配置 (config.py)
│   │
│   ├── db/               # 数据库配置 (engine, session)
│   │
│   └── main.py           # FastAPI 应用入口
│
├── scripts/
│   ├── import_data.py    # JSON 数据导入脚本
│   └── init_db.sql       # MySQL 建表 SQL
│
├── data/                 # JSON 示例数据
│   ├── documents.json
│   ├── inspection_items.json
│   └── document_changes.json
│
├── alembic/              # 数据库迁移
│
├── requirements.txt      # Python 依赖
└── .env                  # 环境变量配置
```

---

## 数据库设计

### 三张核心表的关系

```
documents ────────────── inspection_items
(SIP主表) 1 ─── N        (检验项目明细)
          │
          └─── N document_changes
               (版本变更记录)
```

### 表1: documents (SIP 主表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| document_id | VARCHAR(100) | 文档编号 **【唯一】** |
| customer | VARCHAR(100) | 客户名称 |
| project | VARCHAR(100) | 项目名称 |
| part_num | VARCHAR(100) | 零件号 |
| part_name | VARCHAR(200) | 零件名称 |
| document_type | VARCHAR(50) | 文档类型 (SIP/SOP) |
| version | VARCHAR(20) | 版本号 |
| drawing_version | VARCHAR(20) | 图纸版本 |
| mold_num | VARCHAR(100) | 模具编号 |
| prepared_date | DATE | 编制日期 |
| status | VARCHAR(20) | 状态 (active/inactive) |

### 表2: inspection_items (检验项目表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| item_id | VARCHAR(50) | 项目编号 **【唯一】** |
| document_id | VARCHAR(100) | 外键 → documents |
| inspection_item | VARCHAR(500) | 检验项目名称 |
| requirements | JSON | 检验要求列表 |
| inspection_method | JSON | 检验方法列表 |
| sampling_plan | JSON | 抽样计划 (AQL, 检验水平) |
| characteristic_level | VARCHAR(10) | 特性等级 (A/B/C) |
| chunk_text | TEXT | 合并文本 (RAG用) |

### 表3: document_changes (变更记录表)

| 字段 | 类型 | 说明 |
|------|------|------|
| id | INT | 主键 |
| change_id | VARCHAR(50) | 变更编号 **【唯一】** |
| document_id | VARCHAR(100) | 外键 → documents |
| version | VARCHAR(20) | 版本号 |
| change_date | DATE | 变更日期 |
| change_content | VARCHAR(1000) | 变更内容 |

---

## 快速开始

### 1. 安装依赖

```bash
cd PQM
pip install -r requirements.txt
```

### 2. 配置数据库

编辑 `.env` 文件：

```env
DB_HOST=localhost
DB_PORT=3306
DB_USER=root
DB_PASSWORD=123456
DB_NAME=pqm_db
```

### 3. 创建数据库

```sql
-- 登录 MySQL
mysql -u root -p

-- 执行建表
source scripts/init_db.sql
```

### 4. 导入示例数据

```bash
python scripts/import_data.py
```

### 5. 启动服务

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 6. 访问 API 文档

- Swagger UI: http://localhost:8000/api/v1/docs
- ReDoc: http://localhost:8000/api/v1/redoc

---

## API 接口

### 文档管理

```
GET    /api/v1/documents                    # 获取文档列表 (分页、过滤)
GET    /api/v1/documents/{document_id}      # 获取单个文档
POST   /api/v1/documents                    # 创建文档
PUT    /api/v1/documents/{document_id}      # 更新文档
DELETE /api/v1/documents/{document_id}      # 删除文档
```

### 检验项目管理

```
GET    /api/v1/inspection-items                         # 获取检验项目列表
GET    /api/v1/inspection-items/{item_id}              # 获取单个检验项目
GET    /api/v1/inspection-items/by-document/{doc_id}   # 获取某文档的所有检验项目
GET    /api/v1/inspection-items/search/text?keyword=   # 全文搜索
POST   /api/v1/inspection-items                         # 创建检验项目
PUT    /api/v1/inspection-items/{item_id}              # 更新检验项目
DELETE /api/v1/inspection-items/{item_id}              # 删除检验项目
```

### 变更记录管理

```
GET    /api/v1/document-changes                     # 获取变更记录列表
GET    /api/v1/document-changes/{change_id}         # 获取单个变更记录
GET    /api/v1/document-changes/by-document/{doc_id} # 获取某文档的所有变更记录
POST   /api/v1/document-changes                     # 创建变更记录
PUT    /api/v1/document-changes/{change_id}         # 更新变更记录
DELETE /api/v1/document-changes/{change_id}         # 删除变更记录
```

---

## Text2SQL 查询示例

Agent 可以将自然语言转换为 SQL 查询：

| 自然语言 | SQL 查询 |
|----------|----------|
| "前横梁的硬度标准是什么？" | SELECT requirements FROM inspection_items WHERE document_id = 'VHST-SIP-SA2HG-014' AND inspection_item LIKE '%硬度%' |
| "哪些项目的AQL是0.65？" | SELECT * FROM inspection_items WHERE JSON_EXTRACT(sampling_plan, '$.aql') = '0.65' |
| "比亚迪项目有哪些SIP？" | SELECT * FROM documents WHERE customer = '比亚迪' AND document_type = 'SIP' |
| "找出所有A级特性的检验项目" | SELECT * FROM inspection_items WHERE characteristic_level = 'A' |

---

## 配置说明

### 应用配置 (app/core/config.py)

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| APP_NAME | 质量检验知识库 | 应用名称 |
| APP_VERSION | 1.0.0 | 版本号 |
| API_PREFIX | /api/v1 | API 路径前缀 |
| DEBUG | False | 调试模式 |

### 数据库配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| DB_HOST | localhost | 数据库主机 |
| DB_PORT | 3306 | 数据库端口 |
| DB_USER | root | 数据库用户 |
| DB_PASSWORD | 123456 | 数据库密码 |
| DB_NAME | pqm_db | 数据库名称 |
| DB_POOL_SIZE | 10 | 连接池大小 |
| DB_MAX_OVERFLOW | 20 | 最大溢出连接数 |

---

## License

MIT#   P Q M _ A G E N T  
 