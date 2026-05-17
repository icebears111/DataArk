<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react" alt="React">
  <img src="https://img.shields.io/badge/LangChain-1.3-339933?style=flat-square" alt="LangChain">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
</p>

# DataArk 🧠

**一个用来学多 Agent 系统的实战项目。**

代码有详细中文注释，每个 Agent 怎么工作、Tool 怎么定义、多轮对话怎么保持——全部照着代码就能看懂。

[English](#) · [中文](#)

---

## 这个项目教什么

### 1. Agent 是什么

不是给 LLM 一个超级 Prompt，而是给 LLM **几把工具**，让它自己决定什么时候用什么工具。

```
用户说"查一下上个月的销售数据"
  → Router Agent 收到 → 判断需要查数据库
  → 调用 Schema Agent 生成 SQL → 执行 → 返回
  → Router Agent 把数据整理成回答
```

### 2. 多 Agent 怎么协作

```
Router（调度员）
  ├─ Tool: list_datasources    → 列出数据源
  ├─ Tool: describe_datasource → 看表结构
  ├─ Tool: query_datasource    → 调 Schema Agent 查数据库
  └─ Tool: search_documents    → 调 Doc Agent 搜文档
```

Router 不懂数据库也不懂文档，它只负责**听懂用户想干什么，然后分给对的人**。

### 3. 每个 Agent 的代码长什么样

**Router Agent** — `backend/app/agents/router_agent.py`

```python
# 定义工具
tools = [
    Tool(name="query_datasource", func=self._query_datasource, ...),
    Tool(name="search_documents", func=self._search_documents, ...),
]

# 把 LLM + 工具 + 提示词 拼成一个 Agent
agent = create_openai_tools_agent(llm, tools, prompt)

# 执行：LLM 思考 → 决定调什么工具 → 得到结果
result = await agent.ainvoke({"input": "查一下 book 表"})
```

**Schema Agent** — `backend/app/agents/schema_agent.py`

```python
# 把自然语言转成 SQL
def generate_sql(self, question, schema):
    prompt = f"根据表结构 {schema}，把问题转成 SQL：{question}"
    return llm.invoke(prompt)
```

**Doc Agent** — `backend/app/agents/doc_agent.py`

```python
# RAG：检索文档块 + 交给 LLM 回答
chunks = search_documents(question)       # 去 ChromaDB 搜
context = "\n".join(chunk["content"] for chunk in chunks)
answer = llm.invoke(f"根据文档内容回答：{context}\n问题：{question}")
```

---

## 跑起来

```bash
cd backend && pip install -r requirements.txt
cp .env.example .env   # 填入 LLM_API_KEY
python run.py          # 后端

cd frontend && npm install && npm run dev  # 前端
```

详细讲解见 [DEVELOPMENT.md](DEVELOPMENT.md)。

---

## 学到的东西能干什么

| 知识点 | 对应文件 |
|--------|----------|
| Agent + Tool 模式 | `router_agent.py` |
| LLM function calling | `router_agent.py:_create_agent()` |
| 多轮对话上下文保持 | `router_agent.py:chat()` |
| NL→SQL 生成 | `schema_agent.py:generate_sql()` |
| LLM 输出安全校验 | `schema_agent.py:_check_sql_safe()` |
| RAG 检索增强生成 | `doc_agent.py` |
| 文本分块 / Embedding | `ingestion.py` |
| 不同 Embedding API 兼容 | `ingestion.py:DashScopeEmbeddings` |

---

## 学习路径

1. **跑起来**，打开聊天界面用一用
2. 读 `router_agent.py` — 理解 Agent 调度 + Tool 定义
3. 读 `schema_agent.py` — NL→SQL 流程
4. 读 `doc_agent.py` + `ingestion.py` — RAG 流程
5. **改代码实验**：加一个新 Tool、换 LLM、调 chunk 参数

---

## License

[MIT](LICENSE)
