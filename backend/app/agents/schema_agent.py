"""
Schema Agent — 数据库查询专家。

功能：
1. 连接数据库，读取表结构（schema）
2. 理解自然语言问题，生成 SQL
3. 执行 SQL 查询，返回结果
4. 用自然语言解释查询结果

安全策略：
- 所有查询设为只读（SELECT ONLY）
- 禁止 DDL/DML 操作
- 查询超时限制
"""

import json
from typing import Optional, List, Dict, Any
from sqlalchemy import create_engine, text, inspect
from sqlalchemy.exc import SQLAlchemyError

from app.config import settings


class SchemaAgent:
    """
    Schema Agent：数据库查询专家。
    
    它能理解数据库结构，把自然语言问题转成 SQL 并执行。
    支持 MySQL / PostgreSQL / SQLite。
    """

    # 危险 SQL 关键字黑名单（阻止写入操作）
    FORBIDDEN_KEYWORDS = [
        "insert", "update", "delete", "drop", "truncate",
        "alter", "create", "replace", "grant", "revoke",
    ]

    def __init__(self):
        """初始化 LLM（和 Router Agent 共用同一套配置）"""
        if settings.LLM_PROVIDER == "ollama":
            from langchain_ollama import ChatOllama
            self.llm = ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0,
            )
        else:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_API_BASE,
                temperature=0,
            )

    def _build_connection_url(self, db_type: str, host: str, port: int,
                              database: str, username: str, password: str) -> str:
        """
        根据数据库类型构造 SQLAlchemy 连接 URL。
        
        SQLAlchemy 使用统一的连接 URL 格式：
            dialect+driver://user:password@host:port/database
        """
        if db_type == "mysql":
            return f"mysql+pymysql://{username}:{password}@{host}:{port}/{database}"
        elif db_type == "postgresql":
            return f"postgresql://{username}:{password}@{host}:{port}/{database}"
        elif db_type == "sqlite":
            # SQLite 不用 host/port，database 就是文件路径
            return f"sqlite:///{database}"
        else:
            raise ValueError(f"不支持的数据库类型: {db_type}")

    def test_connection(self, db_type: str, host: str, port: int,
                        database: str, username: str, password: str) -> bool:
        """
        测试数据库连接是否可用。
        能连上返回 True，连不上抛异常。
        """
        url = self._build_connection_url(db_type, host, port, database, username, password)
        engine = create_engine(url, pool_pre_ping=True)
        try:
            with engine.connect() as conn:
                conn.execute(text("SELECT 1"))
            return True
        except SQLAlchemyError as e:
            raise ConnectionError(f"数据库连接失败: {str(e)}")

    def get_schema(self, db_type: str, host: str, port: int,
                   database: str, username: str, password: str) -> List[Dict]:
        """
        读取数据库的所有表结构。
        
        返回格式：
        [
            {
                "table": "users",
                "columns": [
                    {"name": "id", "type": "int", "nullable": false, "primary_key": true},
                    {"name": "username", "type": "varchar(50)", "nullable": false}
                ]
            }
        ]
        """
        url = self._build_connection_url(db_type, host, port, database, username, password)
        engine = create_engine(url)

        try:
            # SQLAlchemy 的 inspect 可以读取数据库元信息
            inspector = inspect(engine)
            tables = inspector.get_table_names()

            schema = []
            for table_name in tables:
                columns = inspector.get_columns(table_name)
                pk_constraint = inspector.get_pk_constraint(table_name)
                pk_columns = pk_constraint.get("constrained_columns", [])

                col_list = []
                for col in columns:
                    col_list.append({
                        "name": col["name"],
                        "type": str(col["type"]),
                        "nullable": col.get("nullable", True),
                        "primary_key": col["name"] in pk_columns,
                    })

                schema.append({
                    "table": table_name,
                    "columns": col_list,
                })

            return schema
        finally:
            engine.dispose()

    def _check_sql_safe(self, sql: str):
        """
        检查 SQL 是否安全（只读）。
        
        如果 SQL 包含写入/删除/修改关键字，抛异常阻止执行。
        """
        sql_lower = sql.lower().strip()

        # 允许 WITH 开头的 CTE 查询
        # 允许 SELECT 开头的查询
        if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
            raise ValueError(f"只允许 SELECT 查询，检测到: {sql[:50]}...")

        # 检查是否包含危险关键字
        for keyword in self.FORBIDDEN_KEYWORDS:
            # 用单词边界检查，避免匹配到 "selection" 里的 "select"
            if f" {keyword} " in f" {sql_lower} ":
                raise ValueError(f"SQL 包含不允许的操作: {keyword}")

    def generate_sql(self, question: str, schema: List[Dict]) -> str:
        """
        根据自然语言问题和表结构，让 LLM 生成 SQL。
        
        流程：
        1. 把表结构格式化成 LLM 能理解的描述
        2. 提示 LLM 生成对应的 SQL
        3. 解析并返回 SQL
        """
        # 把表结构转成文本描述
        schema_text = self._format_schema_for_llm(schema)

        # 构建提示词
        prompt = f"""你是一个 SQL 专家。根据下面的数据库表结构，把用户的问题翻译成 SQL 查询语句。

数据库表结构：
{schema_text}

要求：
1. 只返回 SQL 语句，不要任何解释
2. 只使用 SELECT 查询
3. 如果问题涉及多表，使用 JOIN
4. 列名使用反引号包裹（如果包含特殊字符）
5. 如果问题不明确，做合理的假设并添加注释

用户问题：{question}

SQL："""

        # 调用 LLM 生成 SQL
        response = self.llm.invoke(prompt)
        sql = response.content.strip()

        # 清理 markdown 代码块标记（LLM 有时会加 ```sql ```）
        if sql.startswith("```"):
            sql = sql.split("\n", 1)[-1]  # 去掉第一行
            sql = sql.rsplit("```", 1)[0]  # 去掉最后一行
        sql = sql.strip()

        # 去掉末尾的分号（子查询里不能有分号）
        sql = sql.rstrip(";").strip()

        return sql

    def execute_sql(self, db_type: str, host: str, port: int,
                    database: str, username: str, password: str,
                    sql: str, limit: int = 100) -> tuple:
        """
        执行 SQL 查询并返回结果。
        
        返回 (列名列表, 数据行列表)
        数据行是字典列表：[{"col1": val1, "col2": val2}, ...]
        """
        # 先检查 SQL 安全性
        self._check_sql_safe(sql)

        url = self._build_connection_url(db_type, host, port, database, username, password)
        engine = create_engine(url)

        try:
            with engine.connect() as conn:
                # 带行数限制，防止查爆内存
                limited_sql = f"SELECT * FROM ({sql}) AS _sub LIMIT {limit}"
                result = conn.execute(text(limited_sql))

                # 获取列名
                columns = list(result.keys())
                # 提取数据
                rows = [dict(row._mapping) for row in result]

                return columns, rows
        finally:
            engine.dispose()

    def explain_result(self, question: str, sql: str, rows: List[Dict]) -> str:
        """
        用自然语言解释查询结果。
        
        LLM 根据原始问题、SQL 和结果数据，生成人类可读的回答。
        """
        # 取前 20 行数据作为上下文（数据太多 token 会超）
        sample = rows[:20]
        data_str = json.dumps(sample, ensure_ascii=False, default=str)

        prompt = f"""你是一个数据分析师。用户问了一个问题，你生成了 SQL 并得到了结果。
请用自然语言解释查询结果，回答用户的问题。

用户问题：{question}
执行的 SQL：{sql}
查询结果（共 {len(rows)} 行，显示前 {len(sample)} 行）：
{data_str}

请用中文回答，重点说明：
1. 数据告诉了我们什么
2. 有什么值得注意的趋势或异常
3. 数据的具体数值（如果有）"""

        response = self.llm.invoke(prompt)
        return response.content.strip()

    def query(self, db_config: Dict, question: str) -> Dict:
        """
        完整查询流程：理解问题 → 生成 SQL → 执行 → 解释。
        
        db_config 包含：
            db_type, host, port, database, username, password, schema
        
        返回：
            sql: 生成的 SQL
            result: 查询结果数据
            explanation: 自然语言解释
        """
        # 1. 获取缓存的表结构
        schema = db_config.get("schema")
        if not schema:
            # 如果没有缓存，实时读取
            schema = self.get_schema(
                db_config["db_type"], db_config["host"], db_config["port"],
                db_config["database"], db_config["username"], db_config["password"],
            )

        # 2. 生成 SQL
        sql = self.generate_sql(question, schema)

        # 3. 执行 SQL
        _, rows = self.execute_sql(
            db_config["db_type"], db_config["host"], db_config["port"],
            db_config["database"], db_config["username"], db_config["password"],
            sql,
        )

        # 4. 解释结果
        explanation = self.explain_result(question, sql, rows)

        return {
            "sql": sql,
            "result": rows,
            "row_count": len(rows),
            "explanation": explanation,
        }

    def _format_schema_for_llm(self, schema: List[Dict]) -> str:
        """
        把表结构格式化成 LLM 容易理解的文本。
        
        输入：
            [{"table": "users", "columns": [{"name": "id", "type": "int"}]}]
        输出：
            表名: users
            字段:
              - id (int) PK
              - username (varchar(50))
        """
        lines = []
        for table in schema:
            lines.append(f"表名: {table['table']}")
            lines.append("  字段:")
            for col in table["columns"]:
                col_desc = f"    - {col['name']} ({col['type']})"
                if col.get("primary_key"):
                    col_desc += " [主键]"
                if not col.get("nullable", True):
                    col_desc += " [非空]"
                lines.append(col_desc)
            lines.append("")
        return "\n".join(lines)
