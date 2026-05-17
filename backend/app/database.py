"""
数据库连接和会话管理。

SQLAlchemy 是 Python 最流行的 ORM（对象关系映射）工具。
它让你用 Python 类（模型）来操作数据库表，不用写 SQL。
"""

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase

from app.config import settings

# 创建数据库引擎
# connect_args={"check_same_thread": False} 是 SQLite 特有的设置
# 因为 FastAPI 是异步框架，多个请求可能在不同线程访问数据库
engine = create_engine(
    settings.DATABASE_URL,
    connect_args={"check_same_thread": False},
)

# 会话工厂：每次请求用它来创建数据库会话
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


class Base(DeclarativeBase):
    """所有数据库模型的基类"""
    pass


def init_db():
    """
    初始化数据库：创建所有表。
    在应用启动时调用一次。
    """
    Base.metadata.create_all(bind=engine)


def get_db():
    """
    FastAPI 依赖注入函数。
    每个请求自动调用，提供数据库会话，请求结束后自动关闭。
    
    用法：
        @router.get("/users")
        def get_users(db: Session = Depends(get_db)):
            ...
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
