"""
聊天相关的 API 路由。

提供两种聊天方式：
1. POST /chat — 普通请求，等全部回复完后返回
2. POST /chat/stream — SSE 流式请求，一个字一个字地返回（体验更好）

SSE = Server-Sent Events
它和 WebSocket 的区别：
- WebSocket：双向通信，前端后端都能主动发消息
- SSE：单向，只能后端推送给前端（适合 AI 回答这种场景）
"""

import json
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents.router_agent import RouterAgent
from app.schemas.chat import ChatRequest, ChatResponse
from app.services.auth import get_current_user
from app.models.user import User

router = APIRouter(prefix="/api/v1/chat", tags=["聊天"])

# 全局 Router Agent 实例（单例模式）
# 第一次使用时创建，之后复用
agent: Optional[RouterAgent] = None


def get_agent() -> RouterAgent:
    """
    获取或创建 Router Agent。
    
    之所以不直接在文件顶部初始化，是因为
    RouterAgent 初始化时要连接 LLM，如果 LLM 配置还没设好会报错。
    延迟初始化让应用至少能启动。
    """
    global agent
    if agent is None:
        agent = RouterAgent()
    return agent


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    user: User = Depends(get_current_user),
):
    """
    普通聊天接口。
    
    调用方式：
        POST /api/v1/chat
        {"message": "你好", "session_id": null}
    
    流程：
    1. 接收用户消息
    2. 交给 Router Agent 处理
    3. Agent 内部思考 + 调用工具（如果需要）
    4. 返回结果
    """
    chat_agent = get_agent()
    reply = await chat_agent.chat(request.message)
    return ChatResponse(reply=reply, session_id=request.session_id or "")


@router.post("/stream")
async def chat_stream(
    request: ChatRequest,
    user: User = Depends(get_current_user),
):
    """
    SSE 流式聊天接口。
    
    调用方式：
        POST /api/v1/chat/stream
        {"message": "你好", "session_id": null}
    
    返回格式（SSE）：
        data: {"token": "你"}
        data: {"token": "好"}
        data: {"done": true}
    
    前端用 EventSource 或 fetch + ReadableStream 读取。
    """
    chat_agent = get_agent()
    reply = await chat_agent.chat(request.message)
    
    async def generate():
        """逐字返回回复内容。"""
        for char in reply:
            yield f"data: {json.dumps({'token': char})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"
    
    return StreamingResponse(
        generate(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
        },
    )
