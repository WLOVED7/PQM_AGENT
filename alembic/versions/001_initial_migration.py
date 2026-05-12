"""initial migration

Revision ID: 001_initial
Revises:
Create Date: 2026-05-08

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_initial'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 创建 documents 表
    op.create_table(
        'documents',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('document_id', sa.String(100), nullable=False, comment='文档编号'),
        sa.Column('customer', sa.String(100), nullable=False, comment='客户名称'),
        sa.Column('project', sa.String(100), nullable=False, comment='项目名称'),
        sa.Column('part_num', sa.String(100), nullable=False, comment='零件号'),
        sa.Column('part_name', sa.String(200), nullable=False, comment='零件名称'),
        sa.Column('document_type', sa.String(50), nullable=False, comment='文档类型'),
        sa.Column('version', sa.String(20), nullable=False, comment='版本号'),
        sa.Column('drawing_version', sa.String(20), nullable=True, comment='图纸版本'),
        sa.Column('mold_num', sa.String(100), nullable=True, comment='模具编号'),
        sa.Column('prepared_date', sa.Date(), nullable=True, comment='编制日期'),
        sa.Column('status', sa.String(20), nullable=False, default='active', comment='状态'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('document_id'),
    )
    op.create_index('idx_customer', 'documents', ['customer'])
    op.create_index('idx_project', 'documents', ['project'])
    op.create_index('idx_part_num', 'documents', ['part_num'])
    op.create_index('idx_document_type', 'documents', ['document_type'])
    op.create_index('idx_status', 'documents', ['status'])
    op.create_index('idx_customer_project', 'documents', ['customer', 'project'])
    op.create_index('idx_document_type_status', 'documents', ['document_type', 'status'])
    op.create_index('idx_part_num_version', 'documents', ['part_num', 'version'])

    # 创建 inspection_items 表
    op.create_table(
        'inspection_items',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('item_id', sa.String(50), nullable=False, comment='检验项目编号'),
        sa.Column('document_id', sa.String(100), nullable=False, comment='文档编号'),
        sa.Column('inspection_id', sa.Integer(), nullable=False, comment='检验顺序号'),
        sa.Column('inspection_item', sa.String(500), nullable=False, comment='检验项目名称'),
        sa.Column('special_characteristic', sa.String(50), nullable=True, comment='特殊特性'),
        sa.Column('characteristic_level', sa.String(10), nullable=True, comment='特性等级'),
        sa.Column('requirements', sa.JSON(), nullable=True, comment='检验要求列表'),
        sa.Column('inspection_method', sa.JSON(), nullable=True, comment='检验方法列表'),
        sa.Column('sampling_plan', sa.JSON(), nullable=True, comment='抽样计划'),
        sa.Column('source_page', sa.Integer(), nullable=True, comment='来源页码'),
        sa.Column('chunk_text', sa.Text(), nullable=True, comment='文本块'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('item_id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.document_id'], ondelete='CASCADE'),
    )
    op.create_index('idx_item_document_id', 'inspection_items', ['document_id'])
    op.create_index('idx_item_inspection_id', 'inspection_items', ['inspection_id'])
    op.create_index('idx_item_inspection_item', 'inspection_items', ['inspection_item'])
    op.create_index('idx_item_characteristic_level', 'inspection_items', ['characteristic_level'])
    op.create_index('idx_item_document_inspection', 'inspection_items', ['document_id', 'inspection_id'])

    # 创建 document_changes 表
    op.create_table(
        'document_changes',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('change_id', sa.String(50), nullable=False, comment='变更编号'),
        sa.Column('document_id', sa.String(100), nullable=False, comment='文档编号'),
        sa.Column('version', sa.String(20), nullable=False, comment='版本号'),
        sa.Column('change_date', sa.Date(), nullable=False, comment='变更日期'),
        sa.Column('change_content', sa.String(1000), nullable=False, comment='变更内容'),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), server_default=sa.func.now(), onupdate=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('change_id'),
        sa.ForeignKeyConstraint(['document_id'], ['documents.document_id'], ondelete='CASCADE'),
    )
    op.create_index('idx_change_document_id', 'document_changes', ['document_id'])
    op.create_index('idx_change_version', 'document_changes', ['version'])
    op.create_index('idx_change_date', 'document_changes', ['change_date'])
    op.create_index('idx_change_document_version', 'document_changes', ['document_id', 'version'])


def downgrade() -> None:
    op.drop_table('document_changes')
    op.drop_table('inspection_items')
    op.drop_table('documents')
