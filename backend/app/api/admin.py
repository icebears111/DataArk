"""
管理后台 API。

需要管理员权限才能访问。
提供用户管理、审计日志查看等功能。
"""

from typing import Optional

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user
from app.services.rbac import require_admin
from app.services.audit import get_logs

router = APIRouter(prefix="/api/v1/admin", tags=["管理"])


@router.get("/users")
def list_users(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """获取所有用户列表（管理员专用）。"""
    users = db.query(User).all()
    return [
        {
            "id": u.id,
            "username": u.username,
            "email": u.email,
            "role": u.role,
            "created_at": u.created_at,
        }
        for u in users
    ]


@router.put("/users/{user_id}/role")
def set_user_role(
    user_id: int,
    data: dict,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    修改用户角色。
    
    只能将用户设为 admin 或 user。
    不能修改自己的角色。
    """
    if user_id == admin.id:
        return {"message": "不能修改自己的角色"}

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"message": "用户不存在"}

    new_role = data.get("role")
    if new_role not in ("admin", "user"):
        return {"message": "角色只能是 admin 或 user"}

    user.role = new_role
    db.commit()
    return {"message": f"用户 {user.username} 的角色已设为 {new_role}"}


@router.delete("/users/{user_id}")
def delete_user(
    user_id: int,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """删除用户（不能删除自己）。"""
    if user_id == admin.id:
        return {"message": "不能删除自己的账号"}

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        return {"message": "用户不存在"}

    db.delete(user)
    db.commit()
    return {"message": f"用户 {user.username} 已删除"}


@router.get("/audit-logs")
def list_audit_logs(
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
    limit: int = Query(50, le=200),
    offset: int = Query(0, ge=0),
    action: Optional[str] = None,
    username: Optional[str] = None,
):
    """
    查看审计日志。
    
    可以按操作类型和用户名筛选。
    """
    logs, total = get_logs(db, limit=limit, offset=offset, action=action, username=username)
    return {
        "total": total,
        "logs": [
            {
                "id": log.id,
                "user_id": log.user_id,
                "username": log.username,
                "action": log.action,
                "detail": log.detail,
                "success": log.success,
                "created_at": log.created_at,
            }
            for log in logs
        ],
    }
