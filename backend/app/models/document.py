"""
文档模型。

存储上传文档的元信息。
实际文件内容存储在 uploads/ 目录。
"""

from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text
from sqlalchemy.sql import func
from app.database import Base


class Document(Base):
    """
    文档表。
    
    用户上传的 PDF/Word/Markdown 文件的元数据。
    文件本体存储在 backend/uploads/ 目录。
    """
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, index=True)
    # 原始文件名
    filename = Column(String(255), nullable=False)
    # 文件类型：pdf / docx / md / txt
    file_type = Column(String(10), nullable=False)
    # 存储路径（相对路径）
    file_path = Column(String(500), nullable=False)
    # 文件大小（字节）
    file_size = Column(Integer, nullable=False)
    # 是否已完成索引（向量化）
    is_indexed = Column(Boolean, default=False)
    # 索引的文本块数量
    chunk_count = Column(Integer, default=0)
    # 创建时间
    created_at = Column(DateTime(timezone=True), server_default=func.now())
