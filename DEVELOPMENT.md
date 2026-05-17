# DataArk 开发文档

## 架构概览

```
┌────────────────────────────────────┐
│           React 前端               │
│ Login | Chat | Docs | Dashboard    │
└────────────────┬───────────────────┘
                 │ REST + SSE
┌────────────────▼───────────────────┐
│           FastAPI 后端              │
│                                    │
│  ┌─────────────────────────────┐  │
│  │       Agent 编排层           │  │
│  │  Router（意图分发）           │  │
│  │     ↓                       │  │
│  │  Schema（NL→SQL）           │  │
│  │  Doc（RAG 问答）             │  │
│  └─────────────────────────────┘  │
│                                    │
│  ┌──────┐ ┌──────┐ ┌───────────┐ │
│  │ JWT  │ │ SQL  │ │ ChromaDB  │ │
│  │ 认证 │ │ite   │ │ 向量库     │ │
│  └──────┘ └──────┘ └───────────┘ │
└────────────────────────────────────┘
```

3 层 Agent 协作架构：**Router Agent** 理解用户意图并分发 → **Schema Agent** 将自然语言转 SQL 查数据库 → **Doc Agent** 对上传文档做 RAG 检索。所有请求经过 JWT 认证 + RBAC 权限 + 审计日志。

---

## 环境配置

### 依赖安装

```bash
cd backend && pip install -r requirements.txt
cd frontend && npm install
```

### 配置文件

复制 `backend/.env.example` 为 `backend/.env`，填入 API Key：

```ini
LLM_API_KEY=sk-xxxxxxxx
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
```

### 启动 / 停止

```bash
# 后端
python backend/run.py              # 启动 → localhost:8000
python backend/run.py --stop       # 停止
python backend/run.py --restart    # 重启

# 前端
cd frontend && npm run dev         # → localhost:5173
```

---

## 项目结构

```
dataark/
├── backend/
│   ├── app/
│   │   ├── agents/           # LangChain Agent 实现
│   │   │   ├── router_agent.py    # 意图分发
│   │   │   ├── schema_agent.py    # NL→SQL
│   │   │   └── doc_agent.py       # 文档 RAG
│   │   ├── api/              # FastAPI 路由
│   │   │   ├── auth.py            # 登录注册
│   │   │   ├── chat.py            # 聊天 + SSE
│   │   │   ├── datasource.py      # 数据源
│   │   │   ├── documents.py       # 文档管理
│   │   │   ├── analytics.py       # 统计
│   │   │   └── admin.py           # 管理后台
│   │   ├── models/           # SQLAlchemy 模型
│   │   ├── services/         # JWT/RBAC/审计/嵌入
│   │   ├── config.py         # 配置
│   │   ├── database.py       # 数据库初始化
│   │   └── main.py           # 入口
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   └── src/
│       ├── pages/            # 6 个页面
│       ├── components/       # 共享组件
│       └── services/         # API + 认证
├── docker-compose.yml
└── DEVELOPMENT.md
```

---

## 开发阶段

| 阶段 | 内容 |
|------|------|
| Phase 1 | 项目骨架：FastAPI + React + JWT 认证 + LangChain Agent |
| Phase 2 | Schema Agent：NL→SQL、数据源管理、多数据库支持 |
| Phase 3 | Doc Agent：文档上传、ChromaDB 向量化、RAG 问答 |
| Phase 4 | 统计看板：数据概览、图表展示 |
| Phase 5 | 企业级：RBAC 权限、审计日志、管理后台 |

---

## 核心模块

### Router Agent

入口 Agent。根据用户意图调用各子 Agent 的工具，保留 `chat_history` 支持多轮对话。

### Schema Agent

连接数据库 → 读取表结构 → LLM 生成 SQL → 执行 → 返回。

安全措施：
- 只读校验：禁止 `INSERT/UPDATE/DELETE/DROP/ALTER`
- 查询上限：默认 `LIMIT 100`
- 分号自动清理：防止子查询语法错误

### Doc Agent

上传 → 解析 → 分块（500 字符/块，50 字符重叠）→ DashScopeEmbeddings 向量化 → ChromaDB 存储。提问时语义检索 Top-K 相关片段。

---

## Bug 记录

### JWT sub 必须是字符串

python-jose 要求 sub 字段为字符串，传入 `user.id`（整数）导致 `jwt.decode()` 报 `Subject must be a string`。

**修复：** `create_access_token(data={"sub": str(user.id)})`，解码后 `int(payload["sub"])`。

### DashScope Embedding 不兼容

LangChain 的 OpenAIEmbeddings 把文本转成 token ID 再发请求，DashScope 只接受原始字符串。

**修复：** 自建 `DashScopeEmbeddings` 类，直接调用 OpenAI SDK。

### uvicorn reload 进程杀不掉

reloader 监视文件变化，杀死 worker 后自动重启。

**修复：** 移去 `reload=True`，改用单进程 + run.py 的 `--stop` 通过 netstat+taskkill 停止。

### 登录 401 误判为 token 过期

前端 `request()` 把所有 HTTP 401 当成 token 过期，但 `/auth/login` 的 401 是密码错误。

**修复：** 非登录接口的 401 才触发过期逻辑。

### `__init__.py` 内容错误

`api/__init__.py` 和 `services/__init__.py` 错误地包含了 `auth.py` 代码。

**修复：** 清空为标准的包初始化文件。

### JSX 注释位置错误

`{/* */}` 注释放在了 `<AuthProvider>` 元素之前，不在任何 JSX 元素内。

**修复：** 删除外层注释。

---

## 开发规范

- Python：PEP 8，中文注释面向中级开发者
- 提交格式：`类型: 描述`（Fix / Add / Refactor / Docs）
- 分支：master（稳定）→ dev（开发）→ feat/* / fix/*
