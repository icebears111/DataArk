"""
数据源相关的 Pydantic 模型。
"""

from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# ----- 请求体 -----

class DatasourceCreate(BaseModel):
    """添加数据源"""
    name: str
    db_type: str           # mysql / postgresql / sqlite
    host: str
    port: int
    database: str
    username: str
    password: str


class DatasourceUpdate(BaseModel):
    """更新数据源"""
    name: Optional[str] = None
    host: Optional[str] = None
    port: Optional[int] = None
    database: Optional[str] = None
    username: Optional[str] = None
    password: Optional[str] = None


class QueryRequest(BaseModel):
    """自然语言查询请求"""
    datasource_id: int
    question: str          # 自然语言问题


class TestConnectionRequest(BaseModel):
    """测试数据库连接"""
    db_type: str
    host: str
    port: int
    database: str
    username: str
    password: str


# ----- 响应体 -----

class DatasourceResponse(BaseModel):
    """数据源信息（返回时隐藏密码）"""
    id: int
    name: str
    db_type: str
    host: str
    port: int
    database: str
    username: str
    is_connected: bool
    created_at: datetime
    last_synced_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DatasourceDetailResponse(DatasourceResponse):
    """数据源详情（包含表结构）"""
    schema_cache: Optional[str] = None


class QueryResponse(BaseModel):
    """查询结果"""
    sql: str               # 生成的 SQL
    result: List[dict]     # 查询结果
    row_count: int         # 行数
    explanation: str       # 自然语言解释


class SchemaInfo(BaseModel):
    """表结构信息"""
    table: str
    columns: List[dict]
