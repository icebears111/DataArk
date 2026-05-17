"""
Doc Agent — 文档问答专家。

基于 RAG（检索增强生成）技术：
1. 用户提问 → 在文档库中检索相关片段
2. 把片段作为上下文组装给 LLM
3. LLM 基于文档内容回答问题
"""

import os
from typing import List
from app.config import settings


class DocAgent:
    """
    Doc Agent：文档问答专家。
    
    它能从用户上传的文档中检索信息并回答问题。
    文档需要先通过 ingestion 服务导入到 ChromaDB。
    """

    def __init__(self):
        """初始化 LLM（和 Router Agent 共用配置）。"""
        if settings.LLM_PROVIDER == "ollama":
            from langchain_ollama import ChatOllama
            self.llm = ChatOllama(
                model=settings.OLLAMA_MODEL,
                base_url=settings.OLLAMA_BASE_URL,
                temperature=0,
            )
        else:
            from langchain_openai import ChatOpenAI
            self.llm = ChatOpenAI(
                model=settings.LLM_MODEL,
                api_key=settings.LLM_API_KEY,
                base_url=settings.LLM_API_BASE,
                temperature=0,
            )

    def query(self, question: str, k: int = 5) -> dict:
        """
        文档问答流程。
        
        1. 在 ChromaDB 中搜索相关文档块
        2. 把文档块作为上下文
        3. LLM 基于文档内容回答
        
        返回：{
            "answer": "LLM 的回答",
            "sources": ["来源文档1", "来源文档2"],
            "chunks": [{"content": "...", "score": 0.95}]
        }
        """
        from app.services.ingestion import search_documents

        # 1. 检索相关文档块
        chunks = search_documents(question, k=k)

        if not chunks:
            return {
                "answer": "没有在已上传的文档中找到相关信息。请先上传相关文档。",
                "sources": [],
                "chunks": [],
            }

        # 2. 组装上下文
        context_parts = []
        sources = set()
        for chunk in chunks:
            context_parts.append(f"[来源: {chunk['metadata'].get('file_path', '未知')}]\n{chunk['content']}")
            source = chunk["metadata"].get("file_path", "")
            if source:
                sources.add(os.path.basename(source))

        context = "\n\n---\n\n".join(context_parts)

        # 3. LLM 回答
        prompt = f"""你是一个文档助手。请根据以下文档内容回答用户的问题。

文档内容：
{context}

用户问题：{question}

要求：
1. 只基于提供的文档内容回答
2. 如果文档中没有相关信息，请明确说"文档中没有提到"
3. 回答要简洁准确
4. 引用文档中的具体内容作为依据"""

        response = self.llm.invoke(prompt)
        answer = response.content.strip()

        return {
            "answer": answer,
            "sources": list(sources),
            "chunks": [{"content": c["content"], "score": c["score"]} for c in chunks],
        }
