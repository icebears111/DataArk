<p align="center">
  <img src="https://img.shields.io/badge/Python-3.12-blue?style=flat-square&logo=python" alt="Python">
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat-square&logo=fastapi" alt="FastAPI">
  <img src="https://img.shields.io/badge/React-18-61DAFB?style=flat-square&logo=react" alt="React">
  <img src="https://img.shields.io/badge/LangChain-1.3-339933?style=flat-square" alt="LangChain">
  <img src="https://img.shields.io/badge/license-MIT-green?style=flat-square" alt="License">
  <img src="https://img.shields.io/badge/PRs-welcome-brightgreen?style=flat-square" alt="PRs">
</p>

# DataArk

> 基于 LangChain 多 Agent 架构的 AI 数据智能平台 —
> 自然语言查数据库、文档 RAG 问答，开箱即用。

[English](#) · [中文](#)

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start](#quick-start)
- [Project Structure](#project-structure)
- [API Overview](#api-overview)
- [Tech Stack](#tech-stack)
- [Configuration](#configuration)
- [Roadmap](#roadmap)
- [Contributing](#contributing)
- [License](#license)

---

## Features

| | Feature | Description |
|---|---|---|
| 🧠 | **Multi-Agent Orchestration** | Router Agent → Schema Agent / Doc Agent, LLM-driven tool routing |
| 🗄️ | **Natural Language → SQL** | Connect MySQL/PostgreSQL/SQLite, auto-generate and execute SQL |
| 📄 | **Document RAG** | Upload PDF/MD/TXT, auto-chunk, vectorize to ChromaDB, semantic search |
| ⚡ | **Real-time Streaming** | SSE-based typing effect for responsive chat experience |
| 🔐 | **Enterprise Security** | JWT auth + bcrypt + RBAC (admin/user) + audit logging |
| 📊 | **Dashboard & Analytics** | Usage stats, top users, agent activity visualization |
| 📦 | **Admin Panel** | User management, system monitoring |
| 🐳 | **Docker Support** | One-command deployment with Docker Compose |

---

## Architecture

```
┌─────────────┐     ┌─────────────────────────────────────┐
│   Browser    │     │          FastAPI Backend             │
│  (React 18)  │────▶│                                     │
│  + Tailwind  │     │  ┌─────────┐  ┌──────────────────┐  │
└─────────────┘     │  │  Auth    │  │   Router Agent    │  │
                    │  │  JWT    │  │  (LLM Dispatcher)  │  │
                    │  └─────────┘  └───────┬────────────┘  │
                    │                       │                │
                    │              ┌────────┴────────┐       │
                    │              │                 │       │
                    │     ┌────────▼────┐    ┌───────▼─────┐ │
                    │     │ Schema Agent│    │  Doc Agent   │ │
                    │     │  NL → SQL   │    │  RAG + LLM   │ │
                    │     └──────┬──────┘    └──────┬───────┘ │
                    │            │                   │         │
                    │     ┌──────▼──────┐    ┌──────▼───────┐ │
                    │     │  MySQL/     │    │   ChromaDB   │ │
                    │     │  SQLite/    │    │  (Vector DB)  │ │
                    │     │ PostgreSQL  │    └──────────────┘ │
                    │     └─────────────┘                     │
                    │                                         │
                    │  ┌──────────┐  ┌──────────────────┐    │
                    │  │  Audit   │  │     RBAC         │    │
                    │  │   Log    │  │  Admin/User      │    │
                    │  └──────────┘  └──────────────────┘    │
                    └─────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites

- Python 3.12+
- Node.js 20+
- A DashScope (Qwen) API key — [get one free](https://bailian.console.aliyun.com/)

### Backend

```bash
cd backend
pip install -r requirements.txt

# Configure your API key
cp .env.example .env
# Edit .env: fill in LLM_API_KEY

python run.py
# → http://localhost:8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# → http://localhost:5173
```

### Docker (full stack)

```bash
cp backend/.env.example .env
# Edit .env: fill in LLM_API_KEY
docker compose up -d
# → http://localhost:80
```

---

## Project Structure

```
dataark/
├── backend/
│   ├── app/
│   │   ├── agents/          # LangChain Agent 实现
│   │   │   ├── router_agent.py    # 意图分发 Agent
│   │   │   ├── schema_agent.py    # NL→SQL 数据库 Agent
│   │   │   └── doc_agent.py       # 文档 RAG Agent
│   │   ├── api/             # FastAPI 路由
│   │   │   ├── auth.py            # 登录/注册
│   │   │   ├── chat.py            # 聊天 + SSE 流式
│   │   │   ├── datasource.py      # 数据源 CRUD
│   │   │   ├── documents.py       # 文档上传/搜索
│   │   │   ├── analytics.py       # 统计分析
│   │   │   └── admin.py           # 管理员接口
│   │   ├── models/          # SQLAlchemy 数据模型
│   │   ├── services/        # JWT/RBAC/审计/嵌入
│   │   ├── config.py        # Pydantic 配置
│   │   ├── database.py      # 数据库初始化
│   │   └── main.py          # FastAPI 入口
│   ├── requirements.txt
│   └── Dockerfile
├── frontend/
│   ├── src/
│   │   ├── pages/           # 6 个功能页面
│   │   ├── components/      # 共享组件
│   │   └── services/        # API 调用 + 认证状态
│   ├── Dockerfile
│   └── package.json
├── docker-compose.yml
└── DEVELOPMENT.md
```

---

## API Overview

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/auth/login` | Login, returns JWT |
| POST | `/api/v1/auth/register` | Register |
| POST | `/api/v1/chat` | Chat with Agent |
| POST | `/api/v1/chat/stream` | SSE streaming chat |
| GET | `/api/v1/datasources` | List data sources |
| POST | `/api/v1/datasources` | Add data source |
| POST | `/api/v1/documents/upload` | Upload & index document |
| POST | `/api/v1/documents/search` | Semantic document search |
| GET | `/api/v1/dashboard/stats` | Dashboard analytics |
| GET | `/api/v1/admin/users` | User management |
| GET | `/api/v1/health` | Health check |

---

## Tech Stack

| Layer | Technology |
|-------|-----------|
| **Backend** | Python 3.12, FastAPI, Uvicorn |
| **AI Framework** | LangChain 1.3 + LangChain-Classic |
| **LLM** | Qwen DashScope (OpenAI-compatible) |
| **Vector DB** | ChromaDB |
| **Database** | SQLite (dev) / MySQL / PostgreSQL |
| **Auth** | JWT + bcrypt + RBAC |
| **Frontend** | React 18, TypeScript, Tailwind CSS, Vite |
| **Deploy** | Docker, Docker Compose |

---

## Configuration

Copy `.env.example` to `.env` and fill in:

```env
LLM_PROVIDER=openai
LLM_API_KEY=sk-your-key-here
LLM_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
LLM_MODEL=qwen-plus
EMBEDDING_MODEL=text-embedding-v2
EMBEDDING_API_BASE=https://dashscope.aliyuncs.com/compatible-mode/v1
```

First registered user gets admin role automatically.

---

## Roadmap

- [x] Phase 1: Project skeleton (FastAPI + React + JWT auth)
- [x] Phase 2: Schema Agent (NL→SQL, multi-DB support)
- [x] Phase 3: Doc Agent (upload, chunk, ChromaDB RAG)
- [x] Phase 4: Dashboard & analytics
- [x] Phase 5: Enterprise features (RBAC, audit, admin panel)
- [ ] Phase 6: LangGraph migration (stateful agent workflow)
- [ ] Phase 7: Multi-tenant support
- [ ] Phase 8: Real-time data source sync

---

## Troubleshooting

See [DEVELOPMENT.md](DEVELOPMENT.md) for known bugs, fixes, and testing notes.

---

## Contributing

PRs welcome! Please read [DEVELOPMENT.md](DEVELOPMENT.md) first.

---

## License

[MIT](LICENSE)
