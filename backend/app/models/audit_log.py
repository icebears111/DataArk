"""
审计日志模型。

记录用户的关键操作，用于安全审计和问题追溯。
"""

from sqlalchemy import Column, Integer, String, DateTime, Text
from sqlalchemy.sql import func
from app.database import Base


class AuditLog(Base):
    """
    审计日志表。
    
    每次用户执行重要操作时，自动记录一条日志。
    包括：谁、什么时间、做了什么、结果如何。
    """
    __tablename__ = "audit_logs"

    id = Column(Integer, primary_key=True, index=True)
    # 操作用户 ID
    user_id = Column(Integer, nullable=False, index=True)
    # 操作用户名（冗余存储，用户删除后日志仍有意义）
    username = Column(String(50), nullable=False)
    # 操作类型：login / query / upload / delete / create_datasource / delete_datasource
    action = Column(String(50), nullable=False, index=True)
    # 操作详情（JSON 格式，存储操作相关的参数和结果）
    detail = Column(Text, nullable=True)
    # 操作是否成功
    success = Column(Integer, default=1)
    # 操作时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
