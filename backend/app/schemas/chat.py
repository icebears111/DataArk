"""
聊天相关的 Pydantic 模型。
"""

from pydantic import BaseModel
from typing import List, Optional


class ChatRequest(BaseModel):
    """聊天请求"""
    message: str           # 用户发的消息
    session_id: Optional[str] = None  # 会话 ID（用于续对话）


class ChatResponse(BaseModel):
    """聊天响应"""
    reply: str             # AI 的回复
    session_id: str        # 会话 ID


class AgentTrace(BaseModel):
    """
    Agent 的推理轨迹。
    用于前端展示"Agent 在想什么"。
    """
    agent_name: str        # 哪个 Agent
    action: str            # 在做什么
    detail: str            # 详细信息
