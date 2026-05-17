# DataArk 开发文档

## 项目简介

基于 LangChain 多 Agent 架构的 AI 数据智能平台。

---

## 一、环境配置

### 1.1 依赖安装

```bash
# 后端
cd backend
pip install -r requirements.txt

# 前端
cd frontend
npm install
```

### 1.2 配置文件

复制 `.env.example` 为 `backend/.env`，填入 LLM API Key：

```ini
LLM_PROVIDER=openai
LLM_API_KEY=sk-xxxxxxxx
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
```

### 1.3 启动 / 停止

```bash
cd backend

python run.py            # 启动（监听 localhost:8000）
python run.py --stop     # 停止
python run.py --restart  # 重启
```

前端：

```bash
cd frontend
npm run dev              # 启动（监听 localhost:5173）
```

---

## 二、已修复 Bug 记录

### Bug 1：`__init__.py` 重复内容导致导入混淆

**现象**：`backend/app/api/__init__.py` 和 `backend/app/services/__init__.py` 错误地包含了 `auth.py` 的完整代码，而不是空的包初始化文件。

**原因**：写入文件时先写了 `__init__.py` 然后又写了 `auth.py`，导致 `__init__.py` 内容错误。

**修复**：清空 `__init__.py`，只保留包注释。

**文件**：`backend/app/api/__init__.py`、`backend/app/services/__init__.py`

---

### Bug 2：PyCharm 报 "在 '__init__.py' 中找不到引用 'config'"

**现象**：PyCharm 静态分析提示 `from app.config import settings` 找不到引用。

**原因**：`app/__init__.py` 没有显式导入子模块，PyCharm 静态分析无法推断 `app.config` 是有效模块。

**修复**：在 `app/__init__.py` 中加入 `import app.config as config`。

**文件**：`backend/app/__init__.py`

---

### Bug 3：前端 JSX 注释位置错误导致编译失败

**现象**：`npm run dev` 报错 `Unexpected token, expected ","` 和 `Unterminated regular expression`。

**原因**：JSX 注释 `{/* */}` 放在了 `<AuthProvider>` 元素**之前**，不在任何 JSX 元素内部，被解析器当成 JavaScript 对象处理。

**修复**：删除外层 JSX 注释，只保留必要的路由结构。

**文件**：`frontend/src/App.tsx`

---

### Bug 4：JWT sub 字段类型错误导致所有 token 验证失败

**现象**：登录成功后，所有需要认证的接口都返回 401 "无法验证凭据"。

**原因**：

`python-jose` 库严格遵循 JWT 标准，要求 `sub`（subject）字段必须是**字符串**。但代码中传入的是 `user.id`（整数），导致 `jwt.decode()` 解码时报 `JWTClaimsError: Subject must be a string`，所有 token 都被拒绝。

**修复（两处）**：

1. `backend/app/api/auth.py:83` — 传参时直接转字符串：
   ```python
   # 改前
   token = create_access_token(data={"sub": user.id})
   # 改后
   token = create_access_token(data={"sub": str(user.id)})
   ```

2. `backend/app/services/auth.py:97-106` — 解码时转回整数：
   ```python
   user_id_str = payload.get("sub")
   if user_id_str is None:
       raise credentials_exception
   user_id = int(user_id_str)
   ```

**文件**：`backend/app/api/auth.py`、`backend/app/services/auth.py`

---

### Bug 5：login 接口 401 被前端误判为 token 过期

**现象**：登录时输入错误密码，前端不显示错误提示，而是直接跳转到登录页并显示"登录已过期"。

**原因**：`api.ts` 的 `request()` 函数把所有 HTTP 401 响应都当成"token 过期"，但 `/auth/login` 接口返回 401 的原因是"用户名或密码错误"。

**修复**：在 `request()` 函数中添加判断：只有非登录接口的 401 才触发 token 过期逻辑。

**文件**：`frontend/src/services/api.ts`

---

### Bug 6：uvicorn reload 模式导致进程杀不掉

**现象**：`python run.py` 启动后用 `taskkill` 杀掉进程，端口仍然被占用，后端自动重启。

**原因**：`uvicorn.run(reload=True)` 会启动一个 reloader 父进程，它持续监控文件变化。杀死 worker 子进程后，reloader 立即重新拉起新的 worker。

**修复**：

1. 移除 `reload=True`，改为单进程运行。
2. 重写 `run.py`，支持 `--stop` 和 `--restart` 参数。
3. `--stop` 通过 `netstat` 查找端口占用进程，用 `taskkill /F` 强制终止。

**文件**：`backend/run.py`

---

## 三、版本日志

| 版本 | 日期 | 说明 |
|------|------|------|
| Phase 1 | 2026-05-16 | 项目骨架：FastAPI + React + JWT 认证 + LangChain Agent |
| Phase 2 | 2026-05-16 | Schema Agent：NL→SQL、数据源管理、MySQL 测试通过 |
| Phase 3 | 2026-05-16 | Doc Agent：文档 RAG、PDF/MD/TXT 上传检索 |
| Phase 4 | 2026-05-16 | 统计看板：数据源/文档概览、图表展示 |
| Phase 5 | 2026-05-16 | 企业级功能：RBAC 权限、审计日志、管理后台 |

---

## 四、Phase 2：Schema Agent + 数据库查询

### 目标

让 AI 能连接用户数据库，通过自然语言直接查询数据。

### 实现方案

```
用户提问: "上月销售额TOP10的商品"

Router Agent 判断 → 需要查数据库
    ↓
Schema Agent
  1. 读取数据库表结构（schema）
  2. 理解用户问题 → 生成 SQL
  3. 执行 SQL → 返回结果
    ↓
Synthesis Agent
  格式化结果 → 返回给用户
```

### 新增文件

```
backend/app/agents/schema_agent.py    # Schema Agent
backend/app/agents/synthesis_agent.py # Synthesis Agent
backend/app/api/datasource.py         # 数据源管理 API
frontend/src/pages/DatasourcePage.tsx  # 数据源管理页面
```

### API 接口

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/datasources` | POST | 添加数据源（数据库连接信息） |
| `/api/v1/datasources` | GET | 列出数据源 |
| `/api/v1/datasources/{id}` | DELETE | 删除数据源 |
| `/api/v1/datasources/{id}/sync` | POST | 同步表结构 |

### 关键实现

1. **Schema Agent** — 基于 LangChain 自定义 Tool 的 SQL 查询 Agent
   - 连接数据库 → 读取表结构 → 缓存 schema
   - 用户提问 → LLM 生成 SQL → 执行 → 返回结果

2. **安全措施**
   - 只读连接：禁止 `INSERT/UPDATE/DELETE/DROP/ALTER` 等关键字
   - SQL 注入防护：校验生成的 SQL 只含 SELECT
   - 查询行数限制：默认 LIMIT 100，防止查爆内存

### 测试覆盖

| 数据库 | 状态 |
|--------|------|
| MySQL | ✅ 已测试通过 |
| PostgreSQL | ⚠️ 未测试 |
| SQLite | ⚠️ 未测试 |

### Phase 2 Bug 记录

| Bug | 现象 | 原因 | 修复 |
|-----|------|------|------|
| SQL 分号报错 | SELECT * FROM (\`book\`;) 报语法错误 | LLM 生成 SQL 末尾带分号，子查询不能有分号 | 自动去掉末尾分号 |
| Agent 不查数据库 | AI 说"功能开发中"不调工具 | 系统提示词写的是"告知用户功能开发中" | 改为指导用工具的提示词 |
| 表名没有说明 | 用户不知道每张表是干嘛的 | describe 只输出表名没有中文描述 | 新增 `_guess_table_description` 方法 |
| 多轮对话断上下文 | 用户说"2"时AI不知道指什么 | chat_history 每次都传空列表 | 保存历史到 self.chat_history |
| list_databases重复提示 | 工具和Agent都追问"查什么" | 工具输出和系统提示词都问了同一句话 | 工具只返回数据，Agent 统一追问 |

---

## 五、Phase 3：Doc Agent + 文档 RAG

### 目标

支持用户上传 PDF/Word/Markdown 文档，AI 能检索文档内容回答问题。

### 实现方案

```
用户上传文档 → 后端接收
    ↓
Ingestion Pipeline
  1. 解析文档（PDF/Word/MD）
  2. 文本分块（chunk）
  3. 向量化（embedding）
  4. 存入向量数据库（ChromaDB）
    ↓
用户提问 → Doc Agent
  1. 向量检索 → 找到相关片段
  2. 组装上下文 → LLM 生成回答
  3. 返回结果 + 引用来源
```

### 新增文件

```
backend/app/agents/doc_agent.py       # Doc Agent
backend/app/services/ingestion.py     # 文档解析 + 向量化
backend/app/api/documents.py          # 文档管理 API
frontend/src/pages/DocumentPage.tsx   # 文档管理页面
```

### API 接口

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/documents/upload` | POST | 上传文档 |
| `/api/v1/documents` | GET | 文档列表 |
| `/api/v1/documents/{id}` | DELETE | 删除文档 |
| `/api/v1/documents/{id}/reindex` | POST | 重新索引 |

### 依赖

需要在 `requirements.txt` 新增：

```
pypdf
docx2txt
unstructured
chromadb
sentence-transformers
```

---

## 六、Phase 4：数据源管理 + 可视化看板

### 目标

统一管理所有数据源（数据库连接、文档、外部 API），提供数据查询统计和可视化。

### 新增功能

1. **数据源管理页面**
   - 添加/编辑/删除数据源
   - 测试连接
   - 同步状态显示

2. **Agent 监控面板**
   - ReactFlow 可视化 Agent 协作流程
   - 实时显示每个 Agent 的推理过程
   - 请求耗时统计

3. **查询统计看板**
   - 每日查询量折线图
   - 热门查询排行
   - Agent 调用分布饼图

### 新增文件

```
frontend/src/pages/DashboardPage.tsx      # 看板页面
frontend/src/pages/MonitorPage.tsx        # Agent 监控页面
frontend/src/components/AgentFlow.tsx     # Agent 流程图组件
frontend/src/components/Charts.tsx        # 图表组件
backend/app/api/analytics.py             # 统计 API
```

### API 接口

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/v1/analytics/queries` | GET | 查询统计 |
| `/api/v1/analytics/popular` | GET | 热门查询 |
| `/api/v1/agents/status` | GET | Agent 状态 |

---

## 七、Phase 5：企业级功能

### 目标

完善的权限管理、多租户隔离、审计日志，使产品达到企业级可用标准。

### 功能列表

#### 7.1 多租户（Multi-Tenant）

- 每个租户独立的数据空间
- 租户间数据完全隔离
- 租户管理员可管理成员

#### 7.2 RBAC 权限控制

| 角色 | 权限 |
|------|------|
| admin | 全部权限 |
| editor | 管理数据源 + 对话 |
| viewer | 只看面板，不能操作 |

#### 7.3 审计日志

- 记录所有敏感操作：登录、数据源变更、文档操作
- 谁、什么时间、做了什么、IP 地址
- 日志查询页面

### 新增文件

```
backend/app/models/tenant.py          # 租户模型
backend/app/models/audit_log.py       # 审计日志模型
backend/app/services/rbac.py          # 权限服务
backend/app/api/admin.py              # 管理 API
frontend/src/pages/AdminPage.tsx      # 管理后台
```

### 新增模块

| 文件 | 说明 |
|------|------|
| `models/audit_log.py` | 审计日志模型 |
| `services/audit.py` | 审计日志服务 |
| `services/rbac.py` | 权限检查中间件 |
| `api/admin.py` | 管理后台 API |
| `pages/AdminPage.tsx` | 管理后台前端 |

### 权限机制

- 第一个注册的用户自动设为 `admin`（管理员）
- 后续注册的用户默认 `user`（普通用户）
- 管理员可以：升权/降权其他用户、删除用户、查看审计日志
- 普通用户看不到管理后台入口

### API 接口

| 端点 | 方法 | 功能 | 权限 |
|------|------|------|------|
| `/api/v1/admin/users` | GET | 用户列表 | admin |
| `/api/v1/admin/users/{id}/role` | PUT | 修改角色 | admin |
| `/api/v1/admin/users/{id}` | DELETE | 删除用户 | admin |
| `/api/v1/admin/audit-logs` | GET | 审计日志 | admin |

---

## 八、开发规范

### 8.1 代码风格

- Python：遵循 PEP 8，使用 `black` 格式化
- TypeScript/React：使用 Prettier
- 注释：中文注释，面向中级开发者

### 8.2 Git 提交规范

```
type: description

type 可选: Fix / Add / Refactor / Docs / Cleanup
示例:
  Fix: JWT sub 字段必须是字符串
  Add: Schema Agent 数据库查询功能
  Docs: 更新开发文档 Phase 2 计划
```

### 8.3 分支策略

```
master       ← 稳定版本
  └── dev    ← 开发分支
       ├── feat/schema-agent
       ├── feat/doc-agent
       └── fix/jwt-auth
```

---

## 九、架构概览

```
┌──────────────────────────────────────────┐
│              React 前端                   │
│  Login | Chat | Docs | Dashboard | Admin │
└──────────────────┬───────────────────────┘
                   │ REST + SSE
┌──────────────────▼───────────────────────┐
│            FastAPI 后端                   │
│                                           │
│  ┌──────────────────────────────────┐    │
│  │       Agent 编排层               │    │
│  │  Router → Schema/Doc/Synthesis   │    │
│  └──────────────────────────────────┘    │
│                                           │
│  ┌──────┐ ┌──────┐ ┌────────┐ ┌──────┐  │
│  │ JWT  │ │ SQL  │ │ChromaDB│ │Audit │  │
│  │ 认证  │ │ite   │ │向量库  │ │日志  │  │
│  └──────┘ └──────┘ └────────┘ └──────┘  │
└──────────────────────────────────────────┘
```

