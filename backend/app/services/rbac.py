"""
RBAC 权限控制服务。

提供角色检查、权限验证等功能。
管理员可以对普通用户进行管理。
"""

from fastapi import Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.services.auth import get_current_user


def require_admin(user: User = Depends(get_current_user)) -> User:
    """
    检查当前用户是否为管理员。
    
    用法：在需要管理员权限的接口上添加这个依赖：
        @router.get("/admin/users")
        def list_users(admin: User = Depends(require_admin)):
            ...
    
    如果用户不是管理员，返回 403 Forbidden。
    """
    if user.role != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="需要管理员权限",
        )
    return user
