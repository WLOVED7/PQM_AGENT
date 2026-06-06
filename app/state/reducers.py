"""
=============================================================================
状态 Reducers (state/reducers.py)
=============================================================================

提供 LangGraph 状态合并的 reducer 函数。
"""


def merge_reducer(current: dict | None, update: dict | None) -> dict:
    """
    合并 reducer - 浅合并，update 覆盖 current 的同名键

    Args:
        current: 当前状态字典
        update: 更新状态字典

    Returns:
        合并后的状态字典
    """
    return {**(current or {}), **(update or {})}