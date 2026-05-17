"""
数据源模型。

存储用户添加的数据库连接信息。
连接字符串（host/user/password/database）加密存储。
"""

from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean
from sqlalchemy.sql import func
from app.database import Base


class Datasource(Base):
    """
    数据源表。
    
    支持 MySQL / PostgreSQL / SQLite 等数据库连接。
    """
    __tablename__ = "datasources"

    id = Column(Integer, primary_key=True, index=True)
    # 数据源名称（用户自定义，如"生产数据库"）
    name = Column(String(100), nullable=False)
    # 数据库类型：mysql / postgresql / sqlite
    db_type = Column(String(20), nullable=False)
    # 连接主机地址
    host = Column(String(255), nullable=False)
    # 端口号（如 MySQL=3306, PostgreSQL=5432）
    port = Column(Integer, nullable=False)
    # 数据库名
    database = Column(String(100), nullable=False)
    # 用户名
    username = Column(String(100), nullable=False)
    # 密码（TODO Phase 5: 使用加密存储）
    password = Column(String(255), nullable=False)
    # 数据源当前连接状态
    is_connected = Column(Boolean, default=False)
    # 缓存的表结构（JSON 字符串）
    # 格式：[{"table": "users", "columns": [{"name": "id", "type": "int"}]}]
    schema_cache = Column(Text, nullable=True)
    # 创建时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    # 最后同步时间
    last_synced_at = Column(DateTime(timezone=True), nullable=True)
