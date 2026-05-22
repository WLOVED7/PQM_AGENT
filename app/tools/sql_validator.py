"""
=============================================================================
SQL 安全校验器 (tools/sql_validator.py)
=============================================================================

【核心功能】
防止 SQL 注入和危险操作。

【校验规则】
1. 只允许 SELECT 语句
2. 禁止：INSERT, UPDATE, DELETE, DROP, ALTER, TRUNCATE, CREATE
3. 禁止：分号 ; 导致的多次语句
4. 禁止：注释 -- /* */
5. 禁止：UNION 注入
6. 限制：LIMIT 数量

【为什么不用参数化？】
参数化可以防止注入，但不能防止：
- 错误查询（如 JOIN 错误）
- 跨表查询（如查询敏感表）
- 过量查询（如 LIMIT 10000）

所以需要双重保护：参数化 + 语法校验。
"""


'''
用于正则表达式匹配。常用来验证 SQL 语法、提取关键词、过滤危险字符等
'''
import re
from typing import Tuple, Optional


class SQLValidationError(Exception):
    """SQL 校验异常"""
    pass


class SQLValidator:
    """SQL 安全校验器"""

    # 允许的 SQL 关键字（仅 SELECT 相关）
    ALLOWED_KEYWORDS = {
        "SELECT", "FROM", "WHERE", "AND", "OR", "NOT", "IN", "NOT IN",
        "LIKE", "NOT LIKE", "BETWEEN", "IS", "NULL", "NOT NULL",
        "ORDER", "BY", "ASC", "DESC", "LIMIT", "OFFSET",
        "GROUP", "GROUP BY", "HAVING", "COUNT", "SUM", "AVG", "MIN", "MAX",
        "AS", "DISTINCT", "JOIN", "LEFT", "RIGHT", "INNER", "OUTER",
        "ON", "EXISTS", "CASE", "WHEN", "THEN", "ELSE", "END",
        "CAST", "DATE", "YEAR", "MONTH", "DAY", "DATE_FORMAT",
        "JSON_EXTRACT", "JSON_VALUE", "JSON_ARRAY", "JSON_OBJECT",
    }

    # 禁止的关键字（危险操作）
    FORBIDDEN_KEYWORDS = {
        "INSERT", "UPDATE", "DELETE", "DROP", "ALTER", "TRUNCATE",
        "CREATE", "GRANT", "REVOKE", "EXEC", "EXECUTE", "CALL",
        "LOAD", "OUTFILE", "DUMPFILE", "INTO",  # 可能有风险
    }

    # 禁止的模式
    FORBIDDEN_PATTERNS = [
        r";\s*\w+",           # 分号后跟语句 (多次注入)
        r"--",                # SQL 注释
        r"/\*.*?\*/",         # C 风格注释
        r";\s*$",             # 以分号结尾
        r"UNION\s+(ALL\s+)?SELECT",  # UNION 注入
        r"INTO\s+OUTFILE",    # 文件写入
        r"LOAD_FILE",         # 文件读取
        r"SLEEP\s*\(",        # 时间注入
        r"BENCHMARK\s*\(",    # 时间注入
    ]

    # 允许的表（白名单）
    ALLOWED_TABLES = {"documents", "inspection_items", "document_changes"}

    def __init__(self, max_limit: int = 100, allowed_tables: set = None):
        """
        初始化校验器

        Args:
            max_limit: 最大返回行数
            allowed_tables: 允许查询的表（白名单）
        """
        self.max_limit = max_limit
        self.allowed_tables = allowed_tables or self.ALLOWED_TABLES

    def validate(self, sql: str) -> Tuple[bool, Optional[str]]:
        """
        校验 SQL 是否安全

        Args:
            sql: 待校验的 SQL 语句

        Returns:
            (是否通过, 错误信息)
        """
        # 去除首尾空白
        sql = sql.strip()

        # 空 SQL
        if not sql:
            return False, "SQL 语句为空"

        # 转大写（统一判断）
        sql_upper = sql.upper()

        # 检查是否以 SELECT 开头
        if not sql_upper.startswith("SELECT"):
            return False, "只允许 SELECT 查询语句"

        # 检查禁止关键字
        for keyword in self.FORBIDDEN_KEYWORDS:
            # 单词边界匹配，避免误判（如 UPDATE 可能匹配到 UPDATED）
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                return False, f"禁止使用: {keyword}"

        # 检查禁止模式
        for pattern in self.FORBIDDEN_PATTERNS:
            if re.search(pattern, sql_upper, re.IGNORECASE):
                return False, f"SQL 包含禁止模式: {pattern}"

        # 提取表名并校验
        tables = self._extract_tables(sql)
        for table in tables:
            if table.lower() not in self.allowed_tables:
                return False, f"禁止查询表: {table}"

        # 校验 LIMIT
        limit_match = re.search(r'LIMIT\s+(\d+)', sql_upper)
        if limit_match:
            limit_value = int(limit_match.group(1))
            if limit_value > self.max_limit:
                return False, f"LIMIT 不能超过 {self.max_limit}"

        return True, None

    def _extract_tables(self, sql: str) -> list:
        """从 SQL 中提取表名"""
        tables = []

        # 匹配 FROM 和 JOIN 后的表名
        patterns = [
            r'FROM\s+`?(\w+)`?',           # FROM table
            r'JOIN\s+`?(\w+)`?',           # JOIN table
            r'LEFT\s+JOIN\s+`?(\w+)`?',    # LEFT JOIN table
            r'RIGHT\s+JOIN\s+`?(\w+)`?',   # RIGHT JOIN table
            r'INNER\s+JOIN\s+`?(\w+)`?',   # INNER JOIN table
        ]

        for pattern in patterns:
            matches = re.findall(pattern, sql, re.IGNORECASE)
            tables.extend(matches)

        return list(set(tables))

    def sanitize(self, sql: str) -> str:
        """清理 SQL（去除潜在危险内容）"""
        # 去除注释
        sql = re.sub(r'--.*$', '', sql, flags=re.MULTILINE)
        sql = re.sub(r'/\*.*?\*/', '', sql, flags=re.DOTALL)

        # 去除尾部分号
        sql = sql.rstrip(';')

        return sql.strip()

    def validate_and_sanitize(self, sql: str) -> str:
        """
        校验并清理 SQL

        Raises:
            SQLValidationError: 校验失败时抛出
        """
        # 先清理
        sql = self.sanitize(sql)

        # 再校验
        is_valid, error = self.validate(sql)
        if not is_valid:
            raise SQLValidationError(error)

        return sql


# 全局实例
sql_validator = SQLValidator()


# sql_validator验证
if __name__ == "__main__":
    from app.utils.logger import get_logger
    logger = get_logger(__name__)
    result = sql_validator.validate("SELECT * FROM documents LIMIT 10")
    logger.debug(f"Validation result: {result}")
