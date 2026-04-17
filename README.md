## DynamicWePubMonitor

微信公众号智能权重监控系统，当前仓库采用前后端同仓结构：

- 后端：FastAPI + SQLAlchemy Async + PostgreSQL + Redis
- 前端：Vue 3 + Vite + Element Plus + Pinia

### 运行环境

项目运行环境统一为 PostgreSQL，不再维护“本地 SQLite / 生产 PostgreSQL”的双环境模式。

- 推荐数据库：`postgresql+asyncpg://postgres:postgres@localhost:5432/dynamicwepubmonitor`
- Redis：`redis://localhost:6379/0`
- Python：`3.12+`
- Node.js：建议 `18+`

### 目录

- `app/`：后端应用
- `frontend/`：前端应用
- `docs/`：设计文档、实现计划、项目记忆
- `tests/`：后端测试

### 常用命令

后端：

```bash
uv run uvicorn app.main:app --reload
pytest -q
```

前端：

```bash
cd frontend
npm install
npm run dev
npm run build
```
