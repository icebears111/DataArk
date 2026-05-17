"""
文档管理 API。

提供文档的上传、列表、删除、检索等功能。
"""

import os
import uuid
from typing import List

from fastapi import APIRouter, Depends, HTTPException, UploadFile, File, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.document import Document
from app.services.auth import get_current_user
from app.services.ingestion import (
    index_document,
    delete_document_index,
    UPLOAD_DIR,
)

router = APIRouter(prefix="/api/v1/documents", tags=["文档"])

# 允许上传的文件类型
ALLOWED_EXTENSIONS = {".pdf", ".md", ".txt", ".docx"}


@router.post("/upload")
async def upload_document(
    file: UploadFile,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    上传并索引文档。
    
    流程：
    1. 保存文件到 uploads/ 目录
    2. 解析文档内容
    3. 分块 + 向量化 + 存入 ChromaDB
    4. 记录文档元数据到数据库
    """
    # 检查文件类型
    file_ext = os.path.splitext(file.filename)[1].lower()
    if file_ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"不支持的文件格式: {file_ext}，支持: {', '.join(ALLOWED_EXTENSIONS)}",
        )

    # 确保上传目录存在
    os.makedirs(UPLOAD_DIR, exist_ok=True)

    # 保存文件（用 UUID 避免文件名冲突）
    saved_name = f"{uuid.uuid4().hex}{file_ext}"
    saved_path = os.path.join(UPLOAD_DIR, saved_name)

    content = await file.read()
    with open(saved_path, "wb") as f:
        f.write(content)

    # 记录到数据库
    doc = Document(
        filename=file.filename,
        file_type=file_ext.lstrip("."),
        file_path=saved_name,
        file_size=len(content),
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)

    # 索引文档（解析 + 分块 + 向量化）
    try:
        chunk_count = index_document(saved_path, doc.id)
        doc.is_indexed = True
        doc.chunk_count = chunk_count
        db.commit()
    except Exception as e:
        doc.is_indexed = False
        db.commit()
        raise HTTPException(status_code=400, detail=f"文档索引失败: {str(e)}")

    return {
        "id": doc.id,
        "filename": doc.filename,
        "file_type": doc.file_type,
        "file_size": doc.file_size,
        "chunk_count": doc.chunk_count,
        "is_indexed": doc.is_indexed,
        "message": "上传并索引成功",
    }


@router.get("")
def list_documents(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出所有已上传的文档。"""
    docs = db.query(Document).order_by(Document.created_at.desc()).all()
    return [
        {
            "id": d.id,
            "filename": d.filename,
            "file_type": d.file_type,
            "file_size": d.file_size,
            "is_indexed": d.is_indexed,
            "chunk_count": d.chunk_count,
            "created_at": d.created_at,
        }
        for d in docs
    ]


@router.delete("/{doc_id}")
def delete_doc(
    doc_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除文档（同时删除向量索引和文件）。"""
    doc = db.query(Document).filter(Document.id == doc_id).first()
    if not doc:
        raise HTTPException(status_code=404, detail="文档不存在")

    # 删除 ChromaDB 中的向量索引
    try:
        delete_document_index(doc_id)
    except Exception:
        pass

    # 删除实际文件
    file_path = os.path.join(UPLOAD_DIR, doc.file_path)
    if os.path.exists(file_path):
        os.remove(file_path)

    # 删除数据库记录
    db.delete(doc)
    db.commit()

    return {"message": "已删除"}


@router.post("/search")
def search_documents(
    query: dict,
    user: User = Depends(get_current_user),
):
    """
    搜索文档。
    
    请求体：{"query": "问题", "k": 5}
    """
    from app.services.ingestion import search_documents as sd

    question = query.get("query", "")
    k = query.get("k", 5)

    if not question:
        raise HTTPException(status_code=400, detail="请输入搜索内容")

    results = sd(question, k=k)
    return {
        "query": question,
        "results": results,
    }
