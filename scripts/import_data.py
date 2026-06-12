"""
=============================================================================
数据导入脚本 (import_data.py)
=============================================================================

【用途】
将 JSON 文件中的数据批量导入到 PostgreSQL 数据库。

【工作流程】
1. 读取 data/ 目录下的 JSON 文件
   - documents.json         → documents 表
   - inspection_items.json  → inspection_items 表
   - document_changes.json  → document_changes 表

2. 对每条数据进行检查
   - 如果已存在 (通过唯一ID判断) → 跳过 (skipped)
   - 如果不存在 → 插入 (created)
   - 如果出错 → 记录错误 (errors)

【使用方式】
```bash
python scripts/import_data.py
python scripts/import_data.py --data-dir /path/to/data
```
"""
import asyncio
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import tqdm

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.db.connection import Database

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)


def load_json(file_path: Path) -> List[Dict[str, Any]]:
    with open(file_path, "r", encoding="utf-8") as f:
        data = json.load(f)
    return data if isinstance(data, list) else [data]


async def import_documents(pool, data_dir: Path) -> Dict[str, int]:
    file_path = data_dir / "documents.json"
    stats = {"total": 0, "created": 0, "skipped": 0, "errors": 0}
    if not file_path.exists():
        logger.warning(f"文件不存在: {file_path}")
        return stats

    data = load_json(file_path)
    async with pool.acquire() as conn:
        for item in tqdm.tqdm(data, desc="导入文档"):
            stats["total"] += 1
            try:
                exists = await conn.fetchval(
                    "SELECT 1 FROM documents WHERE document_id = $1", item["document_id"]
                )
                if exists:
                    stats["skipped"] += 1
                    continue

                await conn.execute(
                    """
                    INSERT INTO documents
                        (document_id, customer, project, part_num, part_name,
                         document_type, version, drawing_version, mold_num,
                         prepared_date, status)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                    """,
                    item["document_id"],
                    item.get("customer", ""),
                    item.get("project", ""),
                    item.get("part_num", ""),
                    item.get("part_name", ""),
                    item.get("document_type", "SIP"),
                    item.get("version", ""),
                    item.get("drawing_version"),
                    item.get("mold_num"),
                    date.fromisoformat(item["prepared_date"]) if item.get("prepared_date") else None,
                    item.get("status", "active"),
                )
                stats["created"] += 1
            except Exception as e:
                logger.error(f"导入文档失败 {item.get('document_id')}: {e}")
                stats["errors"] += 1
    return stats


async def import_inspection_items(pool, data_dir: Path) -> Dict[str, int]:
    file_path = data_dir / "inspection_items.json"
    stats = {"total": 0, "created": 0, "skipped": 0, "errors": 0}
    if not file_path.exists():
        logger.warning(f"文件不存在: {file_path}")
        return stats

    data = load_json(file_path)
    async with pool.acquire() as conn:
        for item in tqdm.tqdm(data, desc="导入检验项目"):
            stats["total"] += 1
            try:
                exists = await conn.fetchval(
                    "SELECT 1 FROM inspection_items WHERE item_id = $1", item["item_id"]
                )
                if exists:
                    stats["skipped"] += 1
                    continue

                # JSON 字段：字符串则先解析，已是 dict/list 直接用
                def to_json(v):
                    if v is None:
                        return None
                    if isinstance(v, str):
                        return json.loads(v) if v else None
                    return v

                await conn.execute(
                    """
                    INSERT INTO inspection_items
                        (item_id, document_id, inspection_id, inspection_item,
                         special_characteristic, characteristic_level,
                         requirements, inspection_method, sampling_plan,
                         source_page, chunk_text)
                    VALUES ($1,$2,$3,$4,$5,$6,$7,$8,$9,$10,$11)
                    """,
                    item["item_id"],
                    item.get("document_id", ""),
                    item.get("inspection_id", 0),
                    item.get("inspection_item", ""),
                    item.get("special_characteristic"),
                    item.get("characteristic_level"),
                    json.dumps(to_json(item.get("requirements")), ensure_ascii=False),
                    json.dumps(to_json(item.get("inspection_method")), ensure_ascii=False),
                    json.dumps(to_json(item.get("sampling_plan")), ensure_ascii=False),
                    item.get("source_page"),
                    item.get("chunk_text"),
                )
                stats["created"] += 1
            except Exception as e:
                logger.error(f"导入检验项目失败 {item.get('item_id')}: {e}")
                stats["errors"] += 1
    return stats


async def import_document_changes(pool, data_dir: Path) -> Dict[str, int]:
    file_path = data_dir / "document_changes.json"
    stats = {"total": 0, "created": 0, "skipped": 0, "errors": 0}
    if not file_path.exists():
        logger.warning(f"文件不存在: {file_path}")
        return stats

    data = load_json(file_path)
    async with pool.acquire() as conn:
        for item in tqdm.tqdm(data, desc="导入变更记录"):
            stats["total"] += 1
            try:
                exists = await conn.fetchval(
                    "SELECT 1 FROM document_changes WHERE change_id = $1", item["change_id"]
                )
                if exists:
                    stats["skipped"] += 1
                    continue

                await conn.execute(
                    """
                    INSERT INTO document_changes
                        (change_id, document_id, version, change_date, change_content)
                    VALUES ($1,$2,$3,$4,$5)
                    """,
                    item["change_id"],
                    item.get("document_id", ""),
                    item.get("version", ""),
                    date.fromisoformat(item["change_date"]),
                    item.get("change_content", ""),
                )
                stats["created"] += 1
            except Exception as e:
                logger.error(f"导入变更记录失败 {item.get('change_id')}: {e}")
                stats["errors"] += 1
    return stats


async def main():
    import argparse

    parser = argparse.ArgumentParser(description="数据导入脚本")
    parser.add_argument("--data-dir", type=str, default="data", help="JSON数据文件目录")
    args = parser.parse_args()
    data_dir = Path(args.data_dir)

    pool = await Database.get_pool()

    all_stats = {
        "documents": await import_documents(pool, data_dir),
        "inspection_items": await import_inspection_items(pool, data_dir),
        "document_changes": await import_document_changes(pool, data_dir),
    }

    await Database.close_pool()

    print("\n" + "=" * 50)
    print("导入统计:")
    print("=" * 50)
    for table, stat in all_stats.items():
        print(f"\n{table}:")
        for key, value in stat.items():
            print(f"  {key}: {value}")
    print("=" * 50)


if __name__ == "__main__":
    asyncio.run(main())
