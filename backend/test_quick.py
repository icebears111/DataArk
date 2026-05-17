"""
DataArk 快速测试脚本。
直接运行这个文件测试所有 API。
"""

import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 先初始化数据库
from app.database import init_db
init_db()
print("DB initialized")

# 测试注册
from app.database import SessionLocal
from app.models.user import User
from app.services.auth import hash_password

db = SessionLocal()
existing = db.query(User).filter(User.username == "test").first()
if not existing:
    user = User(username="test", email="test@test.com", hashed_password=hash_password("123456"))
    db.add(user)
    db.commit()
    print(f"User created: {user.username}")
else:
    print(f"User exists: {existing.username}")
db.close()

# 测试配置
from app.config import settings
print(f"Config OK: model={settings.LLM_MODEL}, provider={settings.LLM_PROVIDER}")

# 测试 Router Agent
from app.agents.router_agent import RouterAgent
import asyncio

async def test_agent():
    agent = RouterAgent()
    reply = await agent.chat("你好，请介绍一下你自己")
    print(f"\nAgent reply:\n{reply}")

asyncio.run(test_agent())

print("\n=== ALL TESTS PASSED ===")
