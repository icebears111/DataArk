"""
认证服务：密码加密、JWT 生成和验证。

关键概念：
  1. passlib — 密码加密库。bcrypt 是目前最安全的密码哈希算法。
  2. python-jose — JWT (JSON Web Token) 库。
     JWT 是一种 token 格式，服务器签发后客户端保存，
     每次请求带上，服务器验证签名即可确认身份。
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
from passlib.context import CryptContext
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from app.config import settings
from app.database import get_db
from app.models.user import User

# ----- 密码加密 -----

# CryptContext 管理加密算法，这里用 bcrypt
# 目前最安全的密码哈希算法之一
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")


def hash_password(password: str) -> str:
    """把明文密码加密成哈希值。数据库中只存哈希值，不存明文。"""
    return pwd_context.hash(password)


def verify_password(plain_password: str, hashed_password: str) -> bool:
    """验证明文密码是否和哈希值匹配。"""
    return pwd_context.verify(plain_password, hashed_password)


# ----- JWT 令牌 -----

# OAuth2PasswordBearer 告诉 FastAPI：
# "这个接口需要登录，token 从 Authorization header 里取"
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")


def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """
    创建 JWT token。
    
    JWT 由三部分组成：
      header.payload.signature
      
    举个例子，如果 data={"sub": 1}，生成的 token 看起来像：
      eyJhbGciOiJIUzI1NiJ9.eyJzdWIiOjF9.xxx
      
    - header: 加密算法
    - payload: 你放的数据（比如用户ID）
    - signature: 用密钥签名，防止篡改
    """
    to_encode = data.copy()
    # 设置过期时间
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    # 用密钥编码成 JWT 字符串
    # 注意：JWT 标准要求 sub 字段必须是字符串
    if "sub" in to_encode and not isinstance(to_encode["sub"], str):
        to_encode["sub"] = str(to_encode["sub"])
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)


def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: Session = Depends(get_db),
) -> User:
    print(f"[auth] 收到 token: {token[:50]}...")
    """
    从 JWT token 中解析出当前用户。
    
    这个函数会：
    1. 解码 token
    2. 取出用户 ID
    3. 查数据库返回用户对象
    
    用法：在需要登录的接口上加 Depends(get_current_user)
    
    例如：
        @router.get("/me")
        def get_me(user: User = Depends(get_current_user)):
            return user
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="无法验证凭据",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        # 解码 JWT
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        # sub 是字符串，需要转回整数才能查数据库
        user_id_str = payload.get("sub")
        if user_id_str is None:
            raise credentials_exception
        user_id = int(user_id_str)
    except JWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"JWT 验证失败: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except (ValueError, TypeError):
        raise credentials_exception

    # 查数据库
    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception
    return user
