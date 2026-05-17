"""
用户模型。

SQLAlchemy 模型 = 数据库表的结构定义。
每个类属性对应一个数据库列。
"""

from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.sql import func

from app.database import Base


class User(Base):
    """
    用户表。
    """
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, nullable=False, index=True)
    email = Column(String(100), unique=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    # 用户角色：admin（管理员） / user（普通用户）
    role = Column(String(20), default="user")
    created_at = Column(DateTime(timezone=True), server_default=func.now())
