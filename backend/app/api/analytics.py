"""
统计与分析 API。

提供数据源使用情况、查询频率等统计信息。
数据来自数据库记录和日志。
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime, timedelta, timezone

from app.database import get_db
from app.models.user import User
from app.models.datasource import Datasource
from app.models.document import Document
from app.services.auth import get_current_user

router = APIRouter(prefix="/api/v1/analytics", tags=["统计"])


@router.get("/summary")
def get_summary(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    获取系统概览数据。
    
    返回数据源数量、文档数量、系统运行时间等信息。
    """
    datasource_count = db.query(Datasource).count()
    document_count = db.query(Document).count()
    indexed_docs = db.query(Document).filter(Document.is_indexed == True).count()
    connected_ds = db.query(Datasource).filter(Datasource.is_connected == True).count()

    return {
        "datasource_count": datasource_count,
        "datasource_connected": connected_ds,
        "document_count": document_count,
        "document_indexed": indexed_docs,
    }


@router.get("/datasources")
def get_datasource_stats(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    数据源统计。
    
    按数据库类型分组统计。
    """
    rows = db.query(
        Datasource.db_type,
        func.count(Datasource.id).label("count"),
    ).group_by(Datasource.db_type).all()

    return [{"type": r.db_type, "count": r.count} for r in rows]
