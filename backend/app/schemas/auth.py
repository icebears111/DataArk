"""
认证相关的 Pydantic 模型。

Pydantic 用于：
1. 请求体校验（前端发来的数据格式对不对）
2. 响应格式定义（返回给前端的数据长什么样）

和 SQLAlchemy 模型的区别：
  - SQLAlchemy 模型 = 数据库里的样子
  - Pydantic schema = API 接口上的样子
"""

from pydantic import BaseModel, EmailStr


# ----- 请求体（前端 → 后端）-----

class UserRegister(BaseModel):
    """注册请求"""
    username: str
    email: str        # 实际项目中可以用 EmailStr 做邮箱格式校验
    password: str


class UserLogin(BaseModel):
    """登录请求"""
    username: str
    password: str


# ----- 响应体（后端 → 前端）-----

class TokenResponse(BaseModel):
    """登录成功返回的 token"""
    access_token: str
    token_type: str = "bearer"


class UserResponse(BaseModel):
    """用户信息（返回时隐藏密码）"""
    id: int
    username: str
    email: str

    class Config:
        # 允许从 ORM 对象创建（即 SQLAlchemy 模型可以直接转成这个 schema）
        from_attributes = True
