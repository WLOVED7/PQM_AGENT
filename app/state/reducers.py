"""
=============================================================================
状态 Reducers (state/reducers.py)
=============================================================================

提供 LangGraph 状态合并的 reducer 函数。
"""
from copy import deepcopy


def merge_reducer(current: dict | None, update: dict | None) -> dict:
    """
    合并 reducer - 深度合并而非覆盖

    Args:
        current: 当前状态字典
        update: 更新状态字典

    Returns:
        合并后的状态字典
    """
    if current is None:
        current = {}
    if update is None:
        update = {}
    result = deepcopy(current)
    result.update(update)
    return result