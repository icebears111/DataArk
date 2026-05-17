# DataArk — 从零学多 Agent 系统

这个项目让你**亲手跑起来**一个完整的多 Agent AI 平台，理解 Agent 之间怎么协作、怎么跟 LLM 配合、怎么落地到真实场景。

---

## 先搞懂：什么是多 Agent 系统？

```
用户说一句话 → 一个 Agent 听懂了 → 分给更专业的 Agent 去干活 → 汇总结果
```

不是用一个超级 Prompt 塞给 LLM，而是让**多个有专长的 Agent 像团队一样协作**。

这个项目里就是 3 个 Agent：

```
Router（调度员）— 听懂用户想干啥，分给下面的人
  ├─ Schema Agent（数据库员）— 会写 SQL 查数据库
  └─ Doc Agent（资料员）— 会在文档里翻答案
```

---

## 架构长什么样

```
┌────────────────────────────────────┐
│           React 前端               │
│ 你打字 → 看到回答                    │
└────────────────┬───────────────────┘
                 │ REST / SSE
┌────────────────▼───────────────────┐
│           FastAPI 后端              │
│                                    │
│  ┌─────────────────────────────┐  │
│  │       Agent 编排层           │  │
│  │  Router（听懂问题→分派）      │  │
│  │     ↓                       │  │
│  │  Schema（听懂了→写 SQL 查）   │  │
│  │  Doc（问文档→去 ChromaDB 翻） │  │
│  └─────────────────────────────┘  │
│                                    │
│  JWT 认证 → RBAC 权限 → 审计日志    │
└────────────────────────────────────┘
```

---

## 跑起来看看

```bash
# 1. 装后端依赖
cd backend && pip install -r requirements.txt

# 2. 配置 API Key（用阿里云百炼，免费）
cp .env.example .env
# 编辑 .env，填入 LLM_API_KEY

# 3. 启动后端
python run.py

# 4. 新开终端，装前端
cd frontend && npm install && npm run dev

# 打开 http://localhost:5173，注册账号，开始用
```

---

## 项目里能学到什么

### 1. Router Agent 怎么写

核心代码 `backend/app/agents/router_agent.py`，关键就几件事：

```python
# 告诉 LLM 有哪些工具可以用
self.tools = [
    Tool(name="query_datasource", func=self._query_datasource, ...),
    Tool(name="search_documents", func=self._search_documents, ...),
]

# 把 LLM + 工具 + 提示词拼成一个 Agent
agent = create_openai_tools_agent(llm, tools, prompt)
executor = AgentExecutor(agent=agent, tools=tools)

# 用户说话 → Agent 自己决定调什么工具 → 返回结果
result = await executor.ainvoke({"input": user_message})
```

**关键理解**：Agent 不是硬编码 if-else，而是把工具列表告诉 LLM，让 LLM 自己决定什么时候用哪个工具。

### 2. 数据库 Agent（Schema Agent）是怎么安全的

文件 `backend/app/agents/schema_agent.py`：

```
用户说"查一下上个月卖了啥"
  → LLM 生成 SELECT ... FROM orders WHERE ...
  → 校验：只允许 SELECT，拦截 INSERT/UPDATE/DELETE/DROP
  → 执行 SQL，返回结果
  → LLM 把结果翻译成人话
```

### 3. 文档 RAG Agent 的完整流程

文件 `backend/app/agents/doc_agent.py` + `backend/app/services/ingestion.py`：

```
用户上传 PDF
  → 解析文本
  → 切成 500 字一块（chunk）
  → 每块转成向量（embedding）
  → 存入 ChromaDB（向量数据库）

用户提问"合同里违约金怎么写的"
  → 把问题也转成向量
  → ChromaDB 里找最像的 5 个块
  → 把找出来的内容 + 问题一起交给 LLM
  → LLM 给出答案
```

### 4. SSE 流式输出是什么

```
普通请求：用户等 → LLM 想完 → 一次性返回（可能等 10 秒）
SSE 流式：用户等 → LLM 想一个字 → 发一个字（打字机效果）
```

代码在 `backend/app/api/chat.py`，核心就一个生成器：

```python
async def generate():
    for char in reply:           # 逐字
        yield f"data: {json.dumps({'token': char})}\n\n"
    yield f"data: {json.dumps({'done': True})}\n\n"
```

### 5. JWT 认证 + 权限控制

```
登录 → 后端验证密码 → 签发 token（含 user_id + 角色）
后续请求 → 带 token → 后端解码 → 识别是谁 + 有没有权限
```

第一个注册的人自动是 `admin`，后面注册的是 `user`。
管理员能看到管理后台，普通用户看不到。

---

## 踩过的坑（学多 Agent 必看）

### 坑 1：LLM 不会自动按你设想的格式调工具

提示词写 `query_datasource 参数格式是 datasource_id|问题`，但 LLM 经常只传问题不传 ID。

**原因**：提示词示例里写的是 `book表的所有数据`，没带 datasource_id，LLM 学到了错误格式。

**教训**：给 LLM 的示例必须**精确等于**函数签名要求的格式，多一个空格都可能跑偏。

### 坑 2：不同 Embedding API 的输入格式不一样

OpenAI 的 Embedding API 接受 token ID，但 DashScope（阿里云）只接受原始字符串。用 LangChain 的 `OpenAIEmbeddings` 直接调用 DashScope 会报错。

**解决**：自己写一个 Embeddings 类，裸调 OpenAI SDK。

### 坑 3：多轮对话上下文保持

Agent 每次调用默认不记住之前说了什么。用户说"查 book 表"，Agent 查了。用户再说"按价格排序"，Agent 不知道"book 表"是什么。

**解决**：在 RouterAgent 里维护 `self.chat_history`，每次调用前把历史组装成 `HumanMessage / AIMessage` 传进去。

### 坑 4：服务进程杀不掉

`uvicorn --reload` 模式会启动一个监控进程，你杀掉 worker，它立刻再起一个。

**解决**：不用 reload，用单进程 + 自己写脚本通过 `netstat + taskkill` 停服务。

### 坑 5：JWT sub 必须是字符串

python-jose 要求 JWT 的 sub 字段是字符串，传整数进去解码就报错。

**解决**：`str(user.id)` 存进去，`int(payload["sub"])` 取出来。

---

## 代码结构速览

```
backend/
├── app/agents/            ← 学 Agent 主要看这里
│   ├── router_agent.py    ← 调度 Agent（入口）
│   ├── schema_agent.py    ← 数据库 Agent
│   └── doc_agent.py       ← 文档 RAG Agent
├── app/api/               ← API 路由
│   ├── chat.py            ← 聊天 + SSE 流式
│   ├── auth.py            ← 登录注册
│   ├── datasource.py      ← 数据源管理
│   └── documents.py       ← 文档上传搜索
├── app/services/
│   ├── auth.py            ← JWT 签发/验证
│   ├── ingestion.py       ← 文档解析 + 向量化
│   └── rbac.py            ← 权限检查
└── app/models/            ← 数据库表模型
```

---

## 推荐的学习路径

1. 先跑起来，用聊天界面试试查数据库和问文档
2. 读 `router_agent.py`，理解 Agent + Tool 的模式
3. 读 `schema_agent.py`，看 Agent 怎么生成和执行 SQL
4. 读 `ingestion.py`，理解 RAG 的全流程
5. 改代码试试：加一个新 Agent、改 Prompt、换 LLM
