"""
数据源管理 API。

提供数据源的 CRUD 操作，以及表结构同步、自然语言查询等功能。
"""

import json
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.user import User
from app.models.datasource import Datasource
from app.schemas.datasource import (
    DatasourceCreate,
    DatasourceUpdate,
    DatasourceResponse,
    DatasourceDetailResponse,
    QueryRequest,
    QueryResponse,
    TestConnectionRequest,
    SchemaInfo,
)
from app.services.auth import get_current_user
from app.agents.schema_agent import SchemaAgent

router = APIRouter(prefix="/api/v1/datasources", tags=["数据源"])

# Schema Agent 全局实例（懒加载）
schema_agent: "SchemaAgent" = None


def get_schema_agent() -> SchemaAgent:
    global schema_agent
    if schema_agent is None:
        schema_agent = SchemaAgent()
    return schema_agent


@router.post("", response_model=DatasourceResponse)
def create_datasource(
    data: DatasourceCreate,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    添加数据源。
    
    保存数据库连接信息，并测试连接是否可用。
    """
    # 测试连接
    agent = get_schema_agent()
    try:
        agent.test_connection(
            data.db_type, data.host, data.port,
            data.database, data.username, data.password,
        )
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # 保存到数据库
    ds = Datasource(
        name=data.name,
        db_type=data.db_type,
        host=data.host,
        port=data.port,
        database=data.database,
        username=data.username,
        password=data.password,
        is_connected=True,
    )
    db.add(ds)
    db.commit()
    db.refresh(ds)
    return ds


@router.get("", response_model=List[DatasourceResponse])
def list_datasources(
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """列出所有数据源（不含密码和表结构）。"""
    return db.query(Datasource).all()


@router.get("/{ds_id}", response_model=DatasourceDetailResponse)
def get_datasource(
    ds_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """获取单个数据源详情（含缓存的表结构）。"""
    ds = db.query(Datasource).filter(Datasource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    return ds


@router.delete("/{ds_id}")
def delete_datasource(
    ds_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """删除数据源。"""
    ds = db.query(Datasource).filter(Datasource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")
    db.delete(ds)
    db.commit()
    return {"message": "已删除"}


@router.post("/test", response_model=dict)
def test_connection(
    data: TestConnectionRequest,
    user: User = Depends(get_current_user),
):
    """测试数据库连接是否可用。"""
    agent = get_schema_agent()
    try:
        agent.test_connection(
            data.db_type, data.host, data.port,
            data.database, data.username, data.password,
        )
        return {"status": "ok", "message": "连接成功"}
    except ConnectionError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{ds_id}/sync", response_model=DatasourceDetailResponse)
def sync_schema(
    ds_id: int,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    同步数据源的表结构。
    
    读取数据库最新的表结构，缓存到 datasource 表的 schema_cache 字段。
    """
    ds = db.query(Datasource).filter(Datasource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    agent = get_schema_agent()
    try:
        schema = agent.get_schema(
            ds.db_type, ds.host, ds.port,
            ds.database, ds.username, ds.password,
        )
        # 序列化成 JSON 字符串存储
        ds.schema_cache = json.dumps(schema, ensure_ascii=False)
        from datetime import datetime, timezone
        ds.last_synced_at = datetime.now(timezone.utc)
        ds.is_connected = True
        db.commit()
        db.refresh(ds)
        return ds
    except Exception as e:
        ds.is_connected = False
        db.commit()
        raise HTTPException(status_code=400, detail=f"同步失败: {str(e)}")


@router.post("/{ds_id}/query", response_model=QueryResponse)
def query_datasource(
    ds_id: int,
    data: QueryRequest,
    db: Session = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """
    用自然语言查询数据源。
    
    流程：
    1. 找到数据源
    2. 获取缓存的表结构（如果没有则实时读取）
    3. Schema Agent 生成 SQL
    4. 执行 SQL
    5. 用自然语言解释结果
    """
    ds = db.query(Datasource).filter(Datasource.id == ds_id).first()
    if not ds:
        raise HTTPException(status_code=404, detail="数据源不存在")

    agent = get_schema_agent()

    # 解析缓存的表结构
    schema = json.loads(ds.schema_cache) if ds.schema_cache else None

    # 如果没有缓存，自动同步
    if not schema:
        schema = agent.get_schema(
            ds.db_type, ds.host, ds.port,
            ds.database, ds.username, ds.password,
        )

    try:
        result = agent.query(
            db_config={
                "db_type": ds.db_type,
                "host": ds.host,
                "port": ds.port,
                "database": ds.database,
                "username": ds.username,
                "password": ds.password,
                "schema": schema,
            },
            question=data.question,
        )
        return QueryResponse(
            sql=result["sql"],
            result=[{k: str(v) for k, v in row.items()} for row in result["result"]],
            row_count=result["row_count"],
            explanation=result["explanation"],
        )
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"查询失败: {str(e)}")
