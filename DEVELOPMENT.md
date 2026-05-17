# DataArk — 从零学多 Agent 系统

这个项目让你**亲手跑起来**一个完整的多 Agent AI 平台。代码有详细中文注释，面向想学多 Agent 但不知道怎么下手的开发者。

---

## 先搞懂：什么是多 Agent 系统

传统的 LLM 调用是这样：

```python
response = llm.invoke("查一下上个月的销售数据")
# LLM 不认识你的数据库，它只能瞎编
```

多 Agent 系统是这样：

```
用户说"查一下上个月的销售数据"
  → Router Agent（调度员）：这件事需要查数据库
  → Schema Agent（数据库员）：我会写 SQL，让我来
      → 连接数据库 → 生成 SQL → 执行 → 返回结果
  → Router Agent：把数据整理成答案给用户
```

**核心思想**：不给 LLM 一个超级复杂的 Prompt，而是给 LLM 几把"工具"，让它自己决定什么时候用哪个。

---

## 跑起来

```bash
cd backend && pip install -r requirements.txt
cp .env.example .env   # 填入 LLM_API_KEY（阿里云百炼免费）
python run.py          # 后端 → localhost:8000

# 另一个终端
cd frontend && npm install && npm run dev  # 前端 → localhost:5173
```

---

## 代码逐段讲解

### 1. Router Agent — 大脑（`backend/app/agents/router_agent.py`）

#### 它做什么

Router Agent 是整个系统的入口。用户说的每句话先进到这里，它决定：
- 需要查数据库 → 调 Schema Agent
- 需要翻文档 → 调 Doc Agent
- 随便聊聊 → 自己回答

#### 关键代码

**① 初始化（第 81–94 行）**

```python
class RouterAgent:
    def __init__(self):
        self.llm = _create_llm()       # 创建 LLM（大语言模型）
        self.tools = self._get_tools()  # 定义可用工具
        self.agent = self._create_agent()  # 组装 Agent
        self.chat_history = []           # 聊天历史
```

初始化做了 4 件事：
1. 创建 LLM 实例（这个 Agent 的"大脑"）
2. 定义工具列表（Agent 能用的"手"）
3. 用 LLM + 工具 + 提示词组装成 Agent
4. 准备一个空的聊天历史列表

**② 工具定义（第 105–133 行）**

```python
def _get_tools(self):
    return [
        Tool(
            name="query_datasource",
            func=self._query_datasource,
            description="查询数据源中的数据。"
                        "输入格式: datasource_id|问题，例如: 1|book表的所有数据",
        ),
        Tool(
            name="search_documents",
            func=self._search_documents,
            description="在已上传的文档中搜索信息。",
        ),
    ]
```

这里定义 Agent 可以使用的工具。每个 Tool 有 3 个要素：
- **name**：工具名，LLM 通过这个名字来调用
- **func**：实际执行的 Python 函数
- **description**：描述工具什么时候用。**这个描述非常关键**——LLM 根据描述来决定是否调用

> **学习要点**：`description` 是 Agent 的"说明书"。写得好，LLM 就知道什么时候该用什么工具；写得差，LLM 就乱调。

**③ 创建 Agent（第 299–332 行）**

```python
def _create_agent(self):
    # 系统提示词——告诉 Agent 它的角色和行为准则
    prompt = ChatPromptTemplate.from_messages([
        ("system", (
            "你是一个智能数据助手，可以使用数据库工具查询数据。\n"
            "查询数据库的流程：\n"
            "1. 调 list_datasources → 显示有哪些数据源给用户看\n"
            "2. 调 describe_datasource → 显示有哪些表\n"
            "3. 等用户说要查哪张表后，调 query_datasource\n"
        )),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    # 把 LLM + 工具 + 提示词 拼成一个 Agent
    agent = create_openai_tools_agent(self.llm, self.tools, prompt)

    # AgentExecutor 是执行引擎
    return AgentExecutor(
        agent=agent,
        tools=self.tools,
        verbose=True,              # 打印思考过程
        handle_parsing_errors=True, # 出错时自动修正
    )
```

**`create_openai_tools_agent` 的工作原理：**

这是一个函数，不是你想象的那种"Agent 类"。它做的就是：
1. 把 LLM 实例绑定到提示词模板上
2. 把工具列表注册到 LLM 的 function calling 能力上
3. 返回一个可调用的 Agent 对象

当用户说"查一下数据"时，执行流程是：

```
LLM 收到提示词 → 思考："我需要查数据库"
  → 返回一个特殊格式："我要调 query_datasource 工具"
  → AgentExecutor 截获这个返回，实际调用 query_datasource 函数
  → 把函数返回结果塞回给 LLM
  → LLM 收到结果，生成最终回答
```

这就是 **ReAct（Reasoning + Acting）模式**：LLM 思考→行动→观察结果→再思考。

**④ 多轮对话（第 334–358 行）**

```python
async def chat(self, message: str) -> str:
    # 把历史对话转成 LangChain 消息格式
    history_messages = []
    for human_msg, ai_msg in self.chat_history:
        history_messages.append(HumanMessage(content=human_msg))
        history_messages.append(AIMessage(content=ai_msg))

    # 调用 Agent
    result = await self.agent.ainvoke({
        "input": message,
        "chat_history": history_messages,
    })

    reply = result["output"]
    self.chat_history.append((message, reply))
    return reply
```

为什么需要自己维护 `chat_history`？

因为 Agent 本身**没有记忆**。每次调用 `ainvoke` 都是独立的。如果不把历史传进去，LLM 不知道之前说过什么：

```
用户：查一下 book 表
Agent：book 表有 id, title, author 三个字段

用户：按价格排序
Agent：对不起，我不太明白"按价格排序"是针对什么
（它忘了刚才在说 book 表）
```

解决方式很简单：每次调用前，把之前所有的对话历史打包成 `HumanMessage` 和 `AIMessage` 格式，塞进 `chat_history` 变量里。

> **学习要点**：多 Agent 系统里的"记忆"不是自动的。你得自己维护、自己传递。

---

### 2. Schema Agent — 数据库专家（`backend/app/agents/schema_agent.py`）

#### 它做什么

把自然语言翻译成 SQL，执行后把结果解释成人话。

```
用户："去年销量最高的 10 本书"
  → Schema Agent 生成 SQL
  → 校验安全 → 执行
  → "2025 年销量最高的书是《三体》，卖了 12,350 本……"
```

#### 关键代码

**① 生成 SQL（第 156–198 行）**

```python
def generate_sql(self, question: str, schema: List[Dict]) -> str:
    # 把表结构格式化成文字
    schema_text = self._format_schema_for_llm(schema)

    # 构造提示词，告诉 LLM 表结构 + 要求
    prompt = f"""你是一个 SQL 专家。根据下面的数据库表结构，把用户的问题翻译成 SQL。

数据库表结构：
{schema_text}

要求：
1. 只返回 SQL 语句，不要任何解释
2. 只使用 SELECT 查询
3. 如果问题涉及多表，使用 JOIN

用户问题：{question}
SQL："""

    response = self.llm.invoke(prompt)
    sql = response.content.strip()

    # 清理 LLM 有时会加的 markdown 代码块标记
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1]  # 去掉第一行 ```sql
        sql = sql.rsplit("```", 1)[0] # 去掉最后一行 ```

    sql = sql.rstrip(";").strip()  # 去掉末尾分号
    return sql
```

这里的关键模式叫 **Prompt 编程**——不给 LLM 复杂的格式约束，而是给它清晰的上下文和明确的输出要求。

**② 安全校验（第 137–154 行）**

```python
FORBIDDEN_KEYWORDS = [
    "insert", "update", "delete", "drop",
    "truncate", "alter", "create", "grant",
]

def _check_sql_safe(self, sql: str):
    sql_lower = sql.lower().strip()

    # 必须是以 SELECT 或 WITH 开头
    if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
        raise ValueError(f"只允许 SELECT 查询")

    # 检查是否包含危险关键字
    for keyword in self.FORBIDDEN_KEYWORDS:
        if f" {keyword} " in f" {sql_lower} ":
            raise ValueError(f"SQL 包含不允许的操作: {keyword}")
```

LLM 生成的 SQL 不一定安全。必须加一层校验：
1. 只能 SELECT，不能 INSERT/UPDATE/DELETE
2. 用 `f" {keyword} "` 做单词边界检查，避免把 `selection` 里的 `select` 也匹配上
3. 执行时加 `LIMIT 100`，防止查爆内存

**③ 结果解释（第 230–254 行）**

```python
def explain_result(self, question, sql, rows):
    sample = rows[:20]  # 只取前 20 行
    data_str = json.dumps(sample, ensure_ascii=False, default=str)

    prompt = f"""你是一个数据分析师。用户问了一个问题，你生成了 SQL 并得到了结果。
请用自然语言解释查询结果。

用户问题：{question}
执行的 SQL：{sql}
查询结果（共 {len(rows)} 行，显示前 20 行）：
{data_str}

请用中文回答，重点说明：
1. 数据告诉了我们什么
2. 有什么值得注意的趋势或异常"""

    response = self.llm.invoke(prompt)
    return response.content.strip()
```

这个函数展示了 **Agent 的"善后"工作**：执行完工具后，还要把原始数据包装成用户能看懂的表达。

**④ 完整查询流程（第 256–295 行）**

```python
def query(self, db_config, question):
    # 1. 获取表结构（有缓存用缓存）
    schema = db_config.get("schema") or self.get_schema(...)

    # 2. LLM 生成 SQL
    sql = self.generate_sql(question, schema)

    # 3. 校验并执行
    _, rows = self.execute_sql(..., sql)

    # 4. LLM 解释结果
    explanation = self.explain_result(question, sql, rows)

    return {"sql": sql, "row_count": len(rows), "explanation": explanation}
```

整个流程就是：**读结构 → 写 SQL → 校验 → 执行 → 解释**。每一步都可能出错，每一步都有对应的错误处理。

---

### 3. Doc Agent — 文档问答专家（`backend/app/agents/doc_agent.py`）

#### 它做什么

基于 RAG（检索增强生成）技术。用户上传文档后，能针对文档内容提问。

#### 关键代码（第 41–99 行）

```python
def query(self, question: str, k: int = 5) -> dict:
    # 1. 在 ChromaDB 中检索相关文档块
    chunks = search_documents(question, k=k)

    # 2. 组装上下文
    context_parts = []
    for chunk in chunks:
        context_parts.append(
            f"[来源: {chunk['metadata']['file_path']}]\n{chunk['content']}"
        )
    context = "\n\n---\n\n".join(context_parts)

    # 3. LLM 基于文档内容回答
    prompt = f"""你是一个文档助手。请根据以下文档内容回答用户的问题。

文档内容：
{context}

用户问题：{question}

要求：
1. 只基于提供的文档内容回答
2. 如果文档中没有相关信息，请明确说"文档中没有提到"
3. 引用文档中的具体内容作为依据"""

    response = self.llm.invoke(prompt)
    return {"answer": response.content.strip(), "sources": sources, "chunks": chunks}
```

**这就是 RAG 的核心流程：**

```
用户提问 → 去向量数据库搜 → 找到 Top-5 相关段落
  → 把段落 + 问题一起给 LLM → LLM 根据文档内容回答
```

为什么要这么做？因为 LLM 的知识有截止日期，不知道你上传的 PDF 里写了什么。RAG 把"外部知识"实时塞进 LLM 的上下文中，让它基于你的数据回答问题。

---

### 4. Ingestion 服务 — 文档怎么变成向量（`backend/app/services/ingestion.py`）

#### 自定义 Embedding（第 30–78 行）

```python
def _get_embeddings():
    class DashScopeEmbeddings(BaseEmbeddings):
        def __init__(self):
            self.client = OpenAI(
                api_key=settings.LLM_API_KEY,
                base_url=settings.EMBEDDING_API_BASE,
            )
            self.model = settings.EMBEDDING_MODEL

        def embed_documents(self, texts):
            response = self.client.embeddings.create(
                model=self.model, input=texts,
            )
            return [item.embedding for item in response.data]

        def embed_query(self, text):
            response = self.client.embeddings.create(
                model=self.model, input=text,
            )
            return response.data[0].embedding

    return DashScopeEmbeddings()
```

为什么不用 LangChain 自带的 OpenAIEmbeddings？

因为 DashScope（阿里云百炼）的 Embedding API **只接受原始字符串**。而 LangChain 的 OpenAIEmbeddings 内部会把文本切成 token ID 再发请求——DashScope 不认识 token ID，报错。

**这就是集成第三方 API 的常见坑**：框架提供的封装不一定兼容你的 API 提供商。有时候必须自己写一个适配器。

#### 文档切块（第 132–149 行）

```python
def chunk_text(text, chunk_size=500, chunk_overlap=50):
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        separators=["\n\n", "\n", "。", ".", " ", ""],
    )
    return splitter.split_text(text)
```

为什么需要切块？
- LLM 上下文有限（比如 8K tokens），不能把整个 PDF 都塞进去
- 用户问"合同里违约金怎么写的"，你不需要整本合同的全部内容，找到相关那一段就够了
- 多段相关的块组合起来比单一段落信息更丰富

**chunk_size=500 和 chunk_overlap=50**：
- 每块 500 字符
- 相邻块重叠 50 字符，防止一句话刚好被切到两段导致语义断裂

#### 完整索引流程（第 152–186 行）

```python
def index_document(file_path, doc_id):
    text = parse_document(file_path)      # 1. 解析文件
    chunks = chunk_text(text)             # 2. 切成小块
    lc_docs = [LCDocument(...) for ...]   # 3. 包装成 Document 对象
    vector_store.add_documents(lc_docs)   # 4. 存入 ChromaDB
    return len(chunks)
```

#### 搜索（第 189–208 行）

```python
def search_documents(query, k=5):
    vector_store = _get_vector_store()
    results = vector_store.similarity_search_with_score(query, k=k)
    return [{"content": doc.page_content, "score": score} for doc, score in results]
```

`similarity_search_with_score` 做的是：
1. 把 `query` 也转成向量
2. 在 ChromaDB 里算余弦相似度
3. 返回最相似的 k 个块，附上相似度分数

---

### 5. Chat API — SSE 流式输出（`backend/app/api/chat.py`）

```python
@router.post("/stream")
async def chat_stream(request, user):
    chat_agent = get_agent()
    reply = await chat_agent.chat(request.message)

    async def generate():
        for char in reply:  # 逐字
            yield f"data: {json.dumps({'token': char})}\n\n"
        yield f"data: {json.dumps({'done': True})}\n\n"

    return StreamingResponse(generate(), media_type="text/event-stream")
```

SSE 和 WebSocket 的区别：
- WebSocket：双向通信，前端后端都能主动发（适合聊天室、游戏）
- SSE：单向，只能后端推给前端（适合 AI 回答——AI 只需要往外说，不需要听）

因为 AI 回答的**生成有延迟**（可能几秒），如果等全部生成完再一次性返回，用户要干等。SSE 让 AI 生成一个字就发一个字，用户看到的是打字机效果。

---

### 6. JWT 认证（`backend/app/services/auth.py`）

```python
def create_access_token(data: dict):
    to_encode = data.copy()
    # sub 必须是字符串！python-jose 严格校验
    if isinstance(to_encode.get("sub"), int):
        to_encode["sub"] = str(to_encode["sub"])
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm="HS256")
```

JWT 的逻辑：
1. 登录时，后端生成一个 token，里面包含 user_id 和过期时间
2. 前端收到 token，存在 localStorage
3. 后续每个请求都在 Header 里带上 token
4. 后端解码 token，知道是谁在请求

**sub 必须是字符串**：python-jose 严格遵循 JWT 标准（RFC 7519），规定 sub 字段必须是字符串。传整数进去解码就报错。这是一个非常典型的"标准合规"问题。

---

## 踩过的坑

### 1. LLM 不会自动按你设想的格式调工具

提示词写 `query_datasource 参数格式是 datasource_id|问题`，但 LLM 只传问题不传 ID。

**原因**：提示词示例写的是 `book表的所有数据`，没带 datasource_id，LLM 学到了错误格式。

**教训**：给 LLM 的示例必须**精确等于**函数签名要求的格式。

### 2. uvicorn reload 杀不掉

`uvicorn --reload` 启动一个监控进程，杀死 worker 后它立刻拉起新的。

**解决**：不用 reload，用单进程 + netstat + taskkill 停服务。

### 3. 登录 401 误判

前端把 HTTP 401 都当成"token 过期"，但登录接口返回 401 是密码错误。

**解决**：只有非登录接口的 401 才触发过期逻辑。

### 4. 多轮对话断上下文

Agent 每次调用不记得之前说过啥。

**解决**：`self.chat_history` 列表 + 每次调用前传进去。

---

## 推荐学习路径

1. **先跑起来** — 注册账号，试试查数据库、问文档，感受 Agent 协作
2. **读 router_agent.py** — 理解 Agent + Tool 模式、提示词设计、chat_history 维护
3. **读 schema_agent.py** — 理解 NL→SQL 流程、安全校验、结果解释
4. **读 ingestion.py + doc_agent.py** — 理解 RAG 全流程
5. **改代码实验**：
   - 加一个新 Agent（比如画图 Agent）
   - 换成 DeepSeek 或 GLM 的 API
   - 调整 chunk_size 看 RAG 效果变化
   - 把 SQLite 换成 MySQL 试试

---

## 代码速查

| 文件 | 学什么 |
|------|--------|
| `router_agent.py` | Agent 调度、Tool 定义、多轮对话 |
| `schema_agent.py` | NL→SQL、函数调用、安全校验 |
| `doc_agent.py` | RAG 检索增强生成 |
| `ingestion.py` | Embedding、文本分块、向量存储 |
| `chat.py` | SSE 流式输出 |
| `auth.py` + `auth.py(api)` | JWT 认证流程 |
