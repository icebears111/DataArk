"""
DataArk 后端入口。

FastAPI 应用启动文件。
运行方式：
    cd backend
    uvicorn app.main:app --reload
    
这个文件做了三件事：
1. 创建 FastAPI 实例
2. 挂载所有路由（API 接口）
3. 启动时初始化数据库
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# 先导入数据模型，确保数据库初始化时所有表结构都注册
import app.models
from app.config import settings
from app.database import init_db
from app.api import auth, chat, datasource, documents, analytics, admin

# 创建 FastAPI 应用实例
# 所有配置都来自 config.py
app = FastAPI(
    title=settings.APP_NAME,
    description="基于 LangChain 多 Agent 架构的 AI 数据智能平台",
    version="0.1.0",
)

# ----- CORS 中间件 -----
# CORS = 跨域资源共享
# 前端（localhost:5173）和后端（localhost:8000）端口不同，
# 浏览器默认会阻止跨域请求，CORS 就是为了解决这个问题。
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],   # 允许所有 HTTP 方法
    allow_headers=["*"],   # 允许所有请求头
)


# ----- 注册路由 -----
# 把 auth.py 和 chat.py 里的接口挂载到应用上
app.include_router(auth.router)
app.include_router(chat.router)
app.include_router(datasource.router)
app.include_router(documents.router)
app.include_router(analytics.router)
app.include_router(admin.router)


@app.on_event("startup")
def on_startup():
    """
    应用启动时自动执行。
    
    目前只做一件事：初始化数据库表。
    如果表已存在，create_all 不会重复创建。
    """
    init_db()


@app.get("/api/v1/health")
def health_check():
    """
    健康检查接口。
    
    用于 Docker 和负载均衡器检查应用是否正常运行。
    """
    return {"status": "ok", "app": settings.APP_NAME}
