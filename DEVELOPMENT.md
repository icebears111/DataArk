# DataArk — 多 Agent 系统详解

从代码层面理解一个完整的多 Agent 协作系统怎么跑起来。

---

## 什么是多 Agent 系统

```
用户说一句话
  → Router Agent（调度员）：听懂了，分给专业的人干
  → Schema Agent（数据库员）：写 SQL 查数据
  → Doc Agent（资料员）：翻文档找答案
  → 汇总回来
```

不是给 LLM 一个超级 Prompt，而是给 LLM **几把工具**，让它自己决定什么时候用什么工具。

---

## 三层 Agent 分工

```
Router（调度员）
  ├─ 工具1: list_datasources    → 列出数据源
  ├─ 工具2: describe_datasource → 看表结构
  ├─ 工具3: query_datasource    → 调 Schema Agent 查数据库
  └─ 工具4: search_documents    → 调 Doc Agent 搜文档
```

Router 本身不做具体查询，它只负责**理解 + 分发**。具体活由子 Agent 干。

---

## Router Agent 逐段拆解

```python
class RouterAgent:
    def __init__(self):
        self.llm = _create_llm()       # 创建 LLM 实例
        self.tools = self._get_tools()  # 定义可用工具
        self.agent = self._create_agent()  # 组装成 Agent
        self.chat_history = []           # 多轮对话历史
```

初始化做了 4 件事，对应 Agent 的 4 个核心要素：大脑（LLM）、手（工具）、身体（Agent 对象）、记忆（chat_history）。

### Tool 定义

```python
def _get_tools(self):
    return [
        Tool(
            name="query_datasource",
            func=self._query_datasource,
            description="查询数据源中的数据。"
                        "输入格式: datasource_id|问题，例如 1|book表的所有数据",
        ),
        Tool(
            name="search_documents",
            func=self._search_documents,
            description="在已上传的文档中搜索信息。",
        ),
    ]
```

每个 Tool 三个要素：
- **name** — LLM 通过这个名字调用
- **func** — 实际执行的 Python 函数
- **description** — LLM 根据描述判断什么时候用这个工具

> **关键**：`description` 决定了 LLM 何时调用、怎么调用。示例必须精确等于函数签名——LLM 会照着示例格式学。

### Agent 组装

```python
def _create_agent(self):
    prompt = ChatPromptTemplate.from_messages([
        ("system", "你是一个智能数据助手，查询数据库分三步走..."),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),
    ])

    agent = create_openai_tools_agent(self.llm, self.tools, prompt)

    return AgentExecutor(
        agent=agent,
        tools=self.tools,
        verbose=True,
        handle_parsing_errors=True,
    )
```

**`create_openai_tools_agent`** 不是类，是一个函数。它把 LLM + 工具 + 提示词绑定在一起，返回一个可调用的 Agent。之后 AgentExecutor 驱动 ReAct 循环：

```
LLM 思考 → 决定调工具 → AgentExecutor 截获并执行 → 结果塞回给 LLM → LLM 继续思考
```

### 多轮对话

```python
async def chat(self, message: str) -> str:
    history_messages = []
    for human_msg, ai_msg in self.chat_history:
        history_messages.append(HumanMessage(content=human_msg))
        history_messages.append(AIMessage(content=ai_msg))

    result = await self.agent.ainvoke({
        "input": message,
        "chat_history": history_messages,
    })

    reply = result["output"]
    self.chat_history.append((message, reply))
    return reply
```

Agent 本身**没有记忆**。每次 ainvoke 都是独立的。不传历史的话：

```
用户：查 book 表
Agent：book 表有 id, title, author

用户：按价格排序
Agent：按什么排序？（忘了在说 book 表）
```

解决方式：自己维护 `chat_history` 列表，每次调用前手动打包成 `HumanMessage/AIMessage` 传进去。

---

## Schema Agent 逐段拆解

### NL → SQL 生成

```python
def generate_sql(self, question, schema):
    schema_text = self._format_schema_for_llm(schema)

    prompt = f"""你是一个 SQL 专家。根据下面的数据库表结构，把用户的问题翻译成 SQL。

表结构：
{schema_text}

要求：
1. 只返回 SQL，不要解释
2. 只使用 SELECT
3. 多表用 JOIN

用户问题：{question}
SQL："""

    response = self.llm.invoke(prompt)
    sql = response.content.strip()

    # 清理 LLM 有时会加的 ```sql 标记
    if sql.startswith("```"):
        sql = sql.split("\n", 1)[-1].rsplit("```", 1)[0]
    sql = sql.rstrip(";").strip()
    return sql
```

**Prompt 编程**：不给格式约束，给清晰的上下文 + 明确的输出要求。

### 安全校验

```python
FORBIDDEN_KEYWORDS = ["insert", "update", "delete", "drop", "alter", "create", "grant"]

def _check_sql_safe(self, sql):
    sql_lower = sql.lower().strip()
    if not (sql_lower.startswith("select") or sql_lower.startswith("with")):
        raise ValueError("只允许 SELECT 查询")

    for keyword in self.FORBIDDEN_KEYWORDS:
        if f" {keyword} " in f" {sql_lower} ":
            raise ValueError(f"包含不允许的操作: {keyword}")
```

LLM 生成的 SQL 不一定安全。必须自己加一层校验：
- 只能用 SELECT
- 单词边界检查（避免匹配到 `selection` 里的 `select`）
- 执行时加 `LIMIT 100`

### 完整查询流程

```python
def query(self, db_config, question):
    schema = db_config.get("schema") or self.get_schema(...)  # 1. 读表结构
    sql = self.generate_sql(question, schema)                   # 2. LLM 生成 SQL
    _, rows = self.execute_sql(..., sql)                        # 3. 校验 + 执行
    explanation = self.explain_result(question, sql, rows)      # 4. LLM 解释结果
    return {"sql": sql, "row_count": len(rows), "explanation": explanation}
```

四步流程：**读结构 → 写 SQL → 执行 → 解释**。

### 表结构 → LLM 可读

```python
def _format_schema_for_llm(self, schema):
    # 输入：[{"table": "users", "columns": [{"name": "id", "type": "int"}]}]
    # 输出：
    #   表名: users
    #     字段:
    #       - id (int) [主键]
    #       - username (varchar(50))
```

把数据库的元数据结构转成 LLM 能理解的文本描述。LLM 读了这个才知道有哪些表、哪些字段。

---

## Doc Agent 逐段拆解

### RAG 核心流程

```python
def query(self, question, k=5):
    # 1. 检索：在 ChromaDB 中找最相似的 k 个文档块
    chunks = search_documents(question, k=k)

    # 2. 组装：把文档块拼成上下文
    context = "\n\n---\n\n".join(
        f"[来源: {c['metadata']['file_path']}]\n{c['content']}"
        for c in chunks
    )

    # 3. 生成：LLM 基于文档内容回答
    prompt = f"""根据以下文档内容回答问题。

文档内容：
{context}

用户问题：{question}

要求：
1. 只基于提供的文档回答
2. 文档中没有就说"没有提到"
3. 引用具体内容作为依据"""

    response = self.llm.invoke(prompt)
    return {"answer": response.content.strip(), "sources": sources}
```

**RAG = 检索 + 生成**。先到向量数据库搜相关段落，再把段落 + 问题一起交给 LLM。

### 文档怎么变成向量

```python
def index_document(file_path, doc_id):
    text = parse_document(file_path)      # 1. PDF/MD/TXT → 纯文本
    chunks = chunk_text(text)             # 2. 500 字一块，50 字重叠
    lc_docs = [LCDocument(...) for ...]   # 3. 包装成 Document
    vector_store.add_documents(lc_docs)   # 4. 存入 ChromaDB
```

### 为什么切块

- LLM 上下文有限，不能塞整本 PDF
- 用户问"违约金怎么写的"，不需要整本合同，找到相关段落就够了
- `chunk_size=500, chunk_overlap=50`：每块 500 字，相邻重叠 50 字避免语义断裂

### 搜索

```python
def search_documents(query, k=5):
    vector_store = _get_vector_store()
    results = vector_store.similarity_search_with_score(query, k=k)
    return [{"content": doc.page_content, "score": score} for doc, score in results]
```

把问题转成向量，在 ChromaDB 里算余弦相似度，返回 Top-K 最相似的块。

---

## 踩坑记录

### 1. Tool 示例格式不对 → LLM 学错

提示词写 `query_datasource 参数格式 datasource_id|问题`，但示例写的是 `book表的所有数据`（没带 ID）。LLM 学到的是错误格式。

**教训**：示例必须精确等于函数签名。

### 2. 多轮对话断上下文

Agent 每次调用传空 `chat_history`，用户说"按价格排序"时 Agent 忘了在说哪个表。

**解决**：`self.chat_history` 列表 + 每次手动传。

### 3. LLM 生成的 SQL 带多余格式

LLM 有时返回 `\`\`\`sql\nSELECT ...\n\`\`\``，有时末尾带分号。

**解决**：`startswith("```")` 去掉标记，`rstrip(";")` 去分号。

### 4. 不同 Embedding API 兼容

OpenAI 的 Embedding API 收 token ID，DashScope 只收原始字符串。用 LangChain 的 `OpenAIEmbeddings` 调 DashScope 报错。

**解决**：自建 `DashScopeEmbeddings`，直接调用 OpenAI SDK。

---

## 推荐学习路径

1. 读 `router_agent.py` — 理解 Agent + Tool + ReAct 循环
2. 读 `schema_agent.py` — NL→SQL + 安全校验
3. 读 `doc_agent.py` + `ingestion.py` — RAG 全流程
4. 改代码实验：
   - 加一个新 Tool（比如搜索网页）
   - 换 LLM 提供商
   - 调 chunk_size 看 RAG 效果变化
