"""
审计日志服务。

提供记录和查询审计日志的功能。
在关键操作（登录、查询、上传等）发生时自动记录。
"""

import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db, SessionLocal
from app.models.user import User
from app.models.audit_log import AuditLog


def add_log(
    user_id: int,
    username: str,
    action: str,
    detail: Optional[dict] = None,
    success: bool = True,
):
    """
    添加一条审计日志。
    
    通常在 API 操作完成后调用，记录关键信息。
    
    参数：
        user_id: 操作人 ID
        username: 操作人用户名
        action: 操作类型（login / query / upload / delete 等）
        detail: 操作的详细参数（可选）
        success: 是否成功
    """
    db = SessionLocal()
    try:
        log = AuditLog(
            user_id=user_id,
            username=username,
            action=action,
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            success=1 if success else 0,
        )
        db.add(log)
        db.commit()
    finally:
        db.close()


def get_logs(
    db: Session,
    limit: int = 50,
    offset: int = 0,
    action: Optional[str] = None,
    username: Optional[str] = None,
) -> tuple:
    """
    查询审计日志列表。
    
    支持按操作类型和用户名过滤。
    
    返回 (日志列表, 总条数)
    """
    query = db.query(AuditLog)

    if action:
        query = query.filter(AuditLog.action == action)
    if username:
        query = query.filter(AuditLog.username.contains(username))

    total = query.count()
    logs = (
        query.order_by(AuditLog.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    return logs, total
