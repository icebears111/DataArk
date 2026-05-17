"""
Router Agent — DataArk 的"大脑"。

这是整个系统的入口 Agent，负责：
1. 理解用户的问题
2. 判断需要哪些专业 Agent 来回答
3. 协调多个 Agent 并行工作
4. 汇总结果返回

技术栈：LangChain 的 Agent + Tool 模式
- Agent：一个由 LLM 驱动的"思考者"，它能决定调用什么工具
- Tool：Agent 可以使用的"工具"，比如查数据库、搜文档、上网搜索
"""

import json
import json
from typing import List, Optional
from sqlalchemy.orm import Session

from app.database import SessionLocal
from app.models.datasource import Datasource

# 注意：LangChain 1.3+ 改了 API，这里用 langchain-classic 保持兼容
# langchain-classic 提供了旧的 AgentExecutor/create_openai_tools_agent API
from langchain_classic.agents import AgentExecutor, create_openai_tools_agent
from langchain_classic.tools import Tool
from langchain_classic.prompts import ChatPromptTemplate, MessagesPlaceholder

from langchain_openai import ChatOpenAI
from langchain_ollama import ChatOllama

from app.config import settings


def _create_llm():
    """
    根据配置创建 LLM 实例。
    
    支持两种方式：
    - openai: 通过 OpenAI 兼容 API（Qwen DashScope、DeepSeek、GLM 等都支持）
    - ollama: 通过本地 Ollama 服务
    """
    if settings.LLM_PROVIDER == "ollama":
        return ChatOllama(
            model=settings.OLLAMA_MODEL,
            base_url=settings.OLLAMA_BASE_URL,
            temperature=0,
        )
    else:
        return ChatOpenAI(
            model=settings.LLM_MODEL,
            api_key=settings.LLM_API_KEY,
            base_url=settings.LLM_API_BASE,
            temperature=0,
        )


class RouterAgent:
    """
    Router Agent：负责理解和分发用户问题。
    
    它本身不做具体的数据查询，而是：
    1. 拆解问题 → 判断需要哪些信息
    2. 分配任务 → 决定调用哪些 Agent
    3. 汇总结果 → 把多个来源的信息整理成答案
    """
    
    def _search_documents(self, question: str) -> str:
        """在已上传的文档中搜索信息。"""
        try:
            from app.agents.doc_agent import DocAgent
            agent = DocAgent()
            result = agent.query(question)
            output = f"回答: {result['answer']}\n"
            if result["sources"]:
                output += f"来源: {', '.join(result['sources'])}"
            return output
        except Exception as e:
            return f"搜索失败: {str(e)}"

    def __init__(self):
        # 初始化 LLM（大语言模型）
        # 这是 Agent 的"大脑"——所有思考和决策都由它完成
        self.llm = _create_llm()
        
        # Agent 可以使用的工具列表
        self.tools = self._get_tools()
        
        # 创建 Agent
        self.agent = self._create_agent()

        # 聊天历史记录（保留多轮对话上下文）
        # 每条记录是 (用户消息, AI回复) 的元组
        self.chat_history: List[tuple] = []
    
    def _get_tools(self) -> List[Tool]:
        """
        定义 Agent 可以使用的工具。
        
        每个 Tool 包含：
        - name: 工具名，LLM 通过这个名字来调用
        - func: 实际执行的函数
        - description: 描述这个工具什么时候用，LLM 据此决定是否调用
        """
        return [
            Tool(
                name="list_datasources",
                func=self._list_datasources,
                description="列出所有已配置的数据源，显示数据源名称和连接信息",
            ),
            Tool(
                name="describe_datasource",
                func=self._describe_datasource,
                description="查看某个数据源有哪些表。输入 datasource_id，返回该数据源的所有表名。"
                            "用户问数据之前，先用这个工具列出有哪些表让用户选择",
            ),
            Tool(
                name="query_datasource",
                func=self._query_datasource,
                description="查询数据源中的数据。先调 list_datasources 和 describe_datasource 确认数据源和表结构，"
                            "然后用户明确说查什么时再用这个工具。输入格式: datasource_id|问题，例如: 1|book表的所有数据",
            ),
            Tool(
                name="search_documents",
                func=self._search_documents,
                description="在已上传的文档中搜索信息。当用户问文档内容时使用。输入格式: 问题，例如: 文档里提到了什么",
            ),
            Tool(
                name="greet",
                func=lambda x: f"你好！我是 DataArk 助手。你说的是：{x}",
                description="当用户打招呼或问简单问题时使用",
            ),
        ]

    def _describe_datasource(self, ds_id_str: str) -> str:
        """
        查看某个数据源的表结构。
        输入 datasource_id，返回所有表名和字段清单。
        """
        try:
            ds_id = int(ds_id_str.strip())
        except ValueError:
            return "格式错误：请输入数据源 ID，例如 1"

        db: Session = SessionLocal()
        try:
            ds = db.query(Datasource).filter(Datasource.id == ds_id).first()
            if not ds:
                return f"数据源 ID={ds_id} 不存在"

            import json
            from app.agents.schema_agent import SchemaAgent
            agent = SchemaAgent()

            # 如果有缓存就用缓存的，否则实时读取
            if ds.schema_cache:
                schema = json.loads(ds.schema_cache)
            else:
                schema = agent.get_schema(
                    ds.db_type, ds.host, ds.port,
                    ds.database, ds.username, ds.password,
                )

            result = f"📋 数据源「{ds.name}」包含以下表：\n\n"
            for i, table in enumerate(schema, 1):
                desc = self._guess_table_description(table)
                if desc:
                    result += f"  {i}. {table['table']}  {desc}\n"
                else:
                    result += f"  {i}. {table['table']}\n"
            return result
        except Exception as e:
            return f"查询表结构失败: {str(e)}"
        finally:
            db.close()

    def _guess_table_description(self, table: dict) -> str:
        """
        根据表名和字段名推测中文含义。
        这样用户看到表名时能知道这张表是干嘛的。
        """
        name = table["table"].lower()
        col_names = [c["name"].lower() for c in table["columns"]]

        # 常见命名模式匹配
        patterns = {
            "user": "用户信息",
            "users": "用户信息",
            "admin": "管理员信息",
            "book": "书籍信息",
            "books": "书籍信息",
            "reader": "读者信息",
            "readers": "读者信息",
            "borrow": "借阅记录",
            "borrow_record": "借阅记录",
            "borrow_records": "借阅记录",
            "category": "分类信息",
            "categories": "分类信息",
            "order": "订单信息",
            "orders": "订单信息",
            "pay": "支付记录",
            "payment": "支付记录",
            "payments": "支付记录",
            "log": "操作日志",
            "logs": "操作日志",
            "config": "配置信息",
            "configs": "配置信息",
            "setting": "系统设置",
            "settings": "系统设置",
            "menu": "菜单信息",
            "menus": "菜单信息",
            "role": "角色信息",
            "roles": "角色信息",
            "permission": "权限信息",
            "permissions": "权限信息",
            "dict": "数据字典",
            "dicts": "数据字典",
            "file": "文件信息",
            "files": "文件信息",
        }

        for key, desc in patterns.items():
            if key == name or name.endswith(f"_{key}") or name.startswith(f"{key}_"):
                return f"— {desc}"

        # 从字段名推测：如果有 title/name 字段可能是"信息表"
        if "title" in col_names or "name" in col_names:
            return "— 基础信息表"
        if "create_time" in col_names or "created_at" in col_names:
            return "— 业务记录表"

        return ""

    def _list_datasources(self, _: str = "") -> str:
        """列出所有已配置的数据源。"""
        db: Session = SessionLocal()
        try:
            dss = db.query(Datasource).all()
            if not dss:
                return "还没有配置数据源。请先在数据源管理页面添加数据库连接。"
            result = "可用数据源：\n"
            for ds in dss:
                status = "✅" if ds.is_connected else "❌"
                result += f"  ID={ds.id} {status} {ds.name} ({ds.db_type}: {ds.host}/{ds.database})\n"
            return result
        finally:
            db.close()

    def _query_datasource(self, input_str: str) -> str:
        """
        查询数据源。
        input_str 格式: "datasource_id|问题"
        """
        try:
            parts = input_str.split("|", 1)
            ds_id = int(parts[0].strip())
            question = parts[1].strip() if len(parts) > 1 else input_str
        except (ValueError, IndexError):
            return "格式错误：调用 query_datasource 时需要 datasource_id|问题，例如 1|book表的所有数据。请先用 list_datasources 查出数据源 ID，再按格式调用。"

        db: Session = SessionLocal()
        try:
            ds = db.query(Datasource).filter(Datasource.id == ds_id).first()
            if not ds:
                return f"数据源 ID={ds_id} 不存在"

            from app.agents.schema_agent import SchemaAgent
            agent = SchemaAgent()
            schema = json.loads(ds.schema_cache) if ds.schema_cache else None

            result = agent.query({
                "db_type": ds.db_type,
                "host": ds.host,
                "port": ds.port,
                "database": ds.database,
                "username": ds.username,
                "password": ds.password,
                "schema": schema,
            }, question)

            output = f"SQL: {result['sql']}\n"
            output += f"结果: {result['row_count']} 行\n"
            output += f"解释: {result['explanation']}"
            return output
        except Exception as e:
            return f"查询失败: {str(e)}"
        finally:
            db.close()
    
    def _create_agent(self) -> AgentExecutor:
        """
        创建 LangChain Agent。
        
        流程：
        1. 定义系统提示词（告诉 Agent 它的角色和行为准则）
        2. 绑定 LLM + 工具 + 提示词
        3. 包装成 AgentExecutor（负责执行循环：思考→行动→观察→思考...）
        """
        # 系统提示词：告诉 Agent 它是谁、该怎么做
        prompt = ChatPromptTemplate.from_messages([
            ("system", (
                "你是一个智能数据助手，可以使用数据库工具查询数据。\n"
                "查询数据库的流程：\n"
                "1. 调 list_datasources → 显示有哪些数据源给用户看\n"
                "2. 调 describe_datasource(数据源ID) → 显示该数据源有哪些表给用户看\n"
                "3. 等用户说要查哪张表后，调 query_datasource(数据源ID|具体问题) → 查询数据\n\n"
                "前两步只是向用户展示有什么数据可用。"
                "展示完后问用户：想查哪张表的数据？\n"
                "用户回复后再执行第三步 query。\n"
                "重要：query_datasource 的参数格式必须是「datasource_id|用户问题」，例如「1|book表的所有数据」。如果不知道 datasource_id，先用 list_datasources 查看。\n"
                "4. 如果用户问的是文档/文件内容，调 search_documents(问题) → 在已上传的文档中搜索\n\n"
                "如果用户只是打招呼或闲聊，用 greet 工具即可。"
            )),
            # 聊天历史（用于多轮对话）
            MessagesPlaceholder(variable_name="chat_history"),
            ("human", "{input}"),
            # Agent 的思考过程记录
            MessagesPlaceholder(variable_name="agent_scratchpad"),
        ])
        
        # 组装 Agent
        agent = create_openai_tools_agent(self.llm, self.tools, prompt)
        
        # AgentExecutor 是实际执行者
        # verbose=True 会打印 Agent 的思考过程（方便调试）
        # handle_parsing_errors 让 Agent 在出错时能自我修正
        return AgentExecutor(
            agent=agent,
            tools=self.tools,
            verbose=True,
            handle_parsing_errors=True,
        )
    
    async def chat(self, message: str) -> str:
        """
        处理用户消息并返回回复。
        
        保留聊天历史记录，让多轮对话有上下文关联。
        每次对话都会记录 (用户说, AI回)，下次传给 LLM。
        """
        # 把之前的聊天历史转换成 LangChain 消息格式
        from langchain_classic.schema import HumanMessage, AIMessage
        history_messages = []
        for human_msg, ai_msg in self.chat_history:
            history_messages.append(HumanMessage(content=human_msg))
            history_messages.append(AIMessage(content=ai_msg))

        result = await self.agent.ainvoke({
            "input": message,
            "chat_history": history_messages,
        })

        reply = result["output"]

        # 保存本轮对话到历史
        self.chat_history.append((message, reply))

        return reply
