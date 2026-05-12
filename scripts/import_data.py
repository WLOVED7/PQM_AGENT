"""
=============================================================================
数据导入脚本 (import_data.py)
=============================================================================

【用途】
将 JSON 文件中的数据批量导入到 MySQL 数据库。

【工作流程】
1. 读取 data/ 目录下的 JSON 文件
   - documents.json         → documents 表
   - inspection_items.json  → inspection_items 表
   - document_changes.json  → document_changes 表

2. 对每条数据进行检查
   - 如果已存在 (通过唯一ID判断) → 跳过 (skipped)
   - 如果不存在 → 插入 (created)
   - 如果出错 → 记录错误 (errors)

3. 使用事务保证数据一致性
   - 出错时自动 rollback
   - 成功时自动 commit

【使用方式】
```bash
# 导入所有数据 (自动创建表)
python scripts/import_data.py

# 重新创建所有表再导入
python scripts/import_data.py --recreate-tables

# 指定数据目录
python scripts/import_data.py --data-dir /path/to/data
```

【输出示例】
导入统计:
documents:
  total: 3
  created: 3
  skipped: 0
  errors: 0
inspection_items:
  total: 6
  created: 6
  skipped: 0
  errors: 0
document_changes:
  total: 12
  created: 12
  skipped: 0
  errors: 0
"""
import json
import logging
import sys
from datetime import date
from pathlib import Path
from typing import Any, Dict, List, Optional

import tqdm

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.db import async_session_factory, engine, Base
from app.models import Document, InspectionItem, DocumentChange


# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


class DataImporter:
    """数据导入器"""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.stats = {
            "documents": {"total": 0, "created": 0, "skipped": 0, "errors": 0},
            "inspection_items": {"total": 0, "created": 0, "skipped": 0, "errors": 0},
            "document_changes": {"total": 0, "created": 0, "skipped": 0, "errors": 0},
        }

    async def import_all(self) -> Dict[str, Any]:
        """导入所有JSON文件"""
        logger.info(f"开始导入数据，目录: {self.data_dir.absolute()}")

        # 导入各类数据
        await self.import_documents()
        await self.import_inspection_items()
        await self.import_document_changes()

        return self.stats

    async def import_documents(self) -> None:
        """导入文档数据"""
        file_path = self.data_dir / "documents.json"
        if not file_path.exists():
            logger.warning(f"文档文件不存在: {file_path}")
            return

        logger.info(f"导入文档数据: {file_path}")
        data = self._load_json(file_path)

        async with async_session_factory() as session:
            for item in tqdm.tqdm(data, desc="导入文档"):
                try:
                    await self._import_document(session, item)
                except Exception as e:
                    logger.error(f"导入文档失败: {item.get('document_id', 'unknown')}, 错误: {e}")
                    self.stats["documents"]["errors"] += 1
                    await session.rollback()

            await session.commit()

        logger.info(
            f"文档导入完成: 总数={self.stats['documents']['total']}, "
            f"创建={self.stats['documents']['created']}, "
            f"跳过={self.stats['documents']['skipped']}, "
            f"错误={self.stats['documents']['errors']}"
        )

    async def _import_document(self, session: AsyncSession, item: Dict[str, Any]) -> None:
        """导入单个文档"""
        self.stats["documents"]["total"] += 1
        document_id = item.get("document_id")

        # 检查是否已存在
        result = await session.execute(
            select(func.count()).select_from(Document).where(Document.document_id == document_id)
        )
        if result.scalar() > 0:
            logger.debug(f"文档已存在，跳过: {document_id}")
            self.stats["documents"]["skipped"] += 1
            return

        # 解析日期
        prepared_date = None
        if item.get("prepared_date"):
            prepared_date = date.fromisoformat(item["prepared_date"])

        db_obj = Document(
            document_id=document_id,
            customer=item.get("customer", ""),
            project=item.get("project", ""),
            part_num=item.get("part_num", ""),
            part_name=item.get("part_name", ""),
            document_type=item.get("document_type", "SIP"),
            version=item.get("version", ""),
            drawing_version=item.get("drawing_version"),
            mold_num=item.get("mold_num"),
            prepared_date=prepared_date,
            status=item.get("status", "active"),
        )
        session.add(db_obj)
        self.stats["documents"]["created"] += 1

    async def import_inspection_items(self) -> None:
        """导入检验项目数据"""
        file_path = self.data_dir / "inspection_items.json"
        if not file_path.exists():
            logger.warning(f"检验项目文件不存在: {file_path}")
            return

        logger.info(f"导入检验项目数据: {file_path}")
        data = self._load_json(file_path)

        async with async_session_factory() as session:
            for item in tqdm.tqdm(data, desc="导入检验项目"):
                try:
                    await self._import_inspection_item(session, item)
                except Exception as e:
                    logger.error(f"导入检验项目失败: {item.get('item_id', 'unknown')}, 错误: {e}")
                    self.stats["inspection_items"]["errors"] += 1
                    await session.rollback()

            await session.commit()

        logger.info(
            f"检验项目导入完成: 总数={self.stats['inspection_items']['total']}, "
            f"创建={self.stats['inspection_items']['created']}, "
            f"跳过={self.stats['inspection_items']['skipped']}, "
            f"错误={self.stats['inspection_items']['errors']}"
        )

    async def _import_inspection_item(self, session: AsyncSession, item: Dict[str, Any]) -> None:
        """导入单个检验项目"""
        self.stats["inspection_items"]["total"] += 1
        item_id = item.get("item_id")

        # 检查是否已存在
        result = await session.execute(
            select(func.count())
            .select_from(InspectionItem)
            .where(InspectionItem.item_id == item_id)
        )
        if result.scalar() > 0:
            logger.debug(f"检验项目已存在，跳过: {item_id}")
            self.stats["inspection_items"]["skipped"] += 1
            return

        # 处理JSON字段
        requirements = item.get("requirements")
        inspection_method = item.get("inspection_method")
        sampling_plan = item.get("sampling_plan")

        # 如果是字符串，尝试解析
        if isinstance(requirements, str):
            requirements = json.loads(requirements) if requirements else None
        if isinstance(inspection_method, str):
            inspection_method = json.loads(inspection_method) if inspection_method else None
        if isinstance(sampling_plan, str):
            sampling_plan = json.loads(sampling_plan) if sampling_plan else None

        db_obj = InspectionItem(
            item_id=item_id,
            document_id=item.get("document_id", ""),
            inspection_id=item.get("inspection_id", 0),
            inspection_item=item.get("inspection_item", ""),
            special_characteristic=item.get("special_characteristic"),
            characteristic_level=item.get("characteristic_level"),
            requirements=requirements,
            inspection_method=inspection_method,
            sampling_plan=sampling_plan,
            source_page=item.get("source_page"),
            chunk_text=item.get("chunk_text"),
        )
        session.add(db_obj)
        self.stats["inspection_items"]["created"] += 1

    async def import_document_changes(self) -> None:
        """导入变更记录数据"""
        file_path = self.data_dir / "document_changes.json"
        if not file_path.exists():
            logger.warning(f"变更记录文件不存在: {file_path}")
            return

        logger.info(f"导入变更记录数据: {file_path}")
        data = self._load_json(file_path)

        async with async_session_factory() as session:
            for item in tqdm.tqdm(data, desc="导入变更记录"):
                try:
                    await self._import_document_change(session, item)
                except Exception as e:
                    logger.error(f"导入变更记录失败: {item.get('change_id', 'unknown')}, 错误: {e}")
                    self.stats["document_changes"]["errors"] += 1
                    await session.rollback()

            await session.commit()

        logger.info(
            f"变更记录导入完成: 总数={self.stats['document_changes']['total']}, "
            f"创建={self.stats['document_changes']['created']}, "
            f"跳过={self.stats['document_changes']['skipped']}, "
            f"错误={self.stats['document_changes']['errors']}"
        )

    async def _import_document_change(self, session: AsyncSession, item: Dict[str, Any]) -> None:
        """导入单个变更记录"""
        self.stats["document_changes"]["total"] += 1
        change_id = item.get("change_id")

        # 检查是否已存在
        result = await session.execute(
            select(func.count())
            .select_from(DocumentChange)
            .where(DocumentChange.change_id == change_id)
        )
        if result.scalar() > 0:
            logger.debug(f"变更记录已存在，跳过: {change_id}")
            self.stats["document_changes"]["skipped"] += 1
            return

        # 解析日期
        change_date = date.fromisoformat(item["change_date"])

        db_obj = DocumentChange(
            change_id=change_id,
            document_id=item.get("document_id", ""),
            version=item.get("version", ""),
            change_date=change_date,
            change_content=item.get("change_content", ""),
        )
        session.add(db_obj)
        self.stats["document_changes"]["created"] += 1

    def _load_json(self, file_path: Path) -> List[Dict[str, Any]]:
        """加载JSON文件"""
        with open(file_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        if isinstance(data, dict):
            # 如果是单个对象，包装成列表
            return [data]
        return data


async def create_tables() -> None:
    """创建所有表"""
    logger.info("创建数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("数据库表创建完成")


async def drop_tables() -> None:
    """删除所有表"""
    logger.warning("删除所有数据库表...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    logger.warning("数据库表已删除")


async def main():
    """主函数"""
    import argparse

    parser = argparse.ArgumentParser(description="数据导入脚本")
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data",
        help="JSON数据文件目录 (默认: data)",
    )
    parser.add_argument(
        "--recreate-tables",
        action="store_true",
        help="删除并重建所有表",
    )
    args = parser.parse_args()

    # 重新创建表
    if args.recreate_tables:
        await drop_tables()
        await create_tables()
    else:
        # 确保表存在
        await create_tables()

    # 导入数据
    importer = DataImporter(data_dir=args.data_dir)
    stats = await importer.import_all()

    # 打印统计
    print("\n" + "=" * 50)
    print("导入统计:")
    print("=" * 50)
    for table, stat in stats.items():
        print(f"\n{table}:")
        for key, value in stat.items():
            print(f"  {key}: {value}")
    print("=" * 50)


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
