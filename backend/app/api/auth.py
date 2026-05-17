"""
认证相关的 API 路由。

FastAPI 路由 = API 接口的定义。
每个函数对应一个 HTTP 端点（URL + 方法）。
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.schemas.auth import UserRegister, UserLogin, TokenResponse, UserResponse
from app.services.auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
)

# APIRouter 用来组织一组相关的路由
# prefix="/api/v1/auth" 表示所有路由的 URL 都以 /api/v1/auth 开头
router = APIRouter(prefix="/api/v1/auth", tags=["认证"])


@router.post("/register", response_model=UserResponse)
def register(data: UserRegister, db: Session = Depends(get_db)):
    """
    用户注册。
    
    - data: 前端发来的注册信息（用户名、邮箱、密码）
    - db: 数据库会话（FastAPI 自动注入）
    
    流程：
    1. 检查用户名是否已存在
    2. 密码加密
    3. 存入数据库
    4. 返回用户信息（不含密码）
    """
    # 检查用户名是否重复
    existing = db.query(User).filter(
        (User.username == data.username) | (User.email == data.email)
    ).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="用户名或邮箱已存在",
        )
    
    # 检查是否是第一个用户（第一个用户自动设为管理员）
    user_count = db.query(User).count()
    role = "admin" if user_count == 0 else "user"

    # 创建用户
    user = User(
        username=data.username,
        email=data.email,
        hashed_password=hash_password(data.password),
        role=role,
    )
    db.add(user)  # 加入数据库会话
    db.commit()   # 提交事务（真正写入数据库）
    db.refresh(user)  # 刷新对象（获取数据库自动生成的 ID 和创建时间）
    
    return user


@router.post("/login", response_model=TokenResponse)
def login(data: UserLogin, db: Session = Depends(get_db)):
    """
    用户登录。
    
    流程：
    1. 根据用户名查用户
    2. 验证密码
    3. 生成 JWT token
    4. 返回 token
    """
    # 查找用户
    user = db.query(User).filter(User.username == data.username).first()
    if not user or not verify_password(data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="用户名或密码错误",
        )
    
    # 记录登录审计日志
    from app.services.audit import add_log
    add_log(user.id, user.username, "login", {"ip": "未知"})

    # 生成 JWT
    # 注意：JWT 标准要求 sub 字段必须是字符串，不能传整数
    token = create_access_token(data={"sub": str(user.id)})
    
    return TokenResponse(access_token=token)


@router.get("/me", response_model=UserResponse)
def get_me(user: User = Depends(get_current_user)):
    """
    获取当前登录用户的信息。
    
    Depends(get_current_user) 会：
    1. 从请求头中提取 JWT token
    2. 验证 token 有效性
    3. 返回对应的用户对象
    如果 token 无效，自动返回 401 错误。
    """
    return user
