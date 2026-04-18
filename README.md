# Just-We

[![CI](https://github.com/PakhomLeo/dynamicwepubmonitor/actions/workflows/ci.yml/badge.svg)](https://github.com/PakhomLeo/dynamicwepubmonitor/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

中文 | [English](README.en.md)

Just-We 是一个面向微信公众号内容监测的自托管平台。它把抓取账号、监测公众号、文章采集、图片本地化、AI 内容分析、文章导出、Feed 输出、代理管理、限流策略、任务日志和系统管理整合在同一个 Web 控制台里。

项目的核心目标不是做一个通用爬虫框架，而是解决“稳定监测一批公众号内容，并把文章、媒体、AI 判断和运维状态沉淀下来”的完整闭环。默认推荐使用 Docker Compose 一键部署，应用容器同时提供 FastAPI API 和已构建的 Vue 前端静态文件。

## 功能特性

- 用户登录与角色权限：支持 `admin`、`operator`、`viewer` 三类角色。
- 抓取账号管理：支持公众号后台和 WeRead 兼容平台接入，包含二维码登录、健康检查、过期检测、风险状态和失败记录。
- 监测公众号管理：支持从文章链接解析 `biz` / `fakeid`，按用户隔离监测对象，维护 Tier 分层、抓取策略和手动抓取入口。
- 文章采集与归档：保存标题、正文、富文本 HTML、封面图、发布时间、抓取通道、内容指纹、原始抓取元数据和本地化图片。
- AI 分析：支持可配置的文本分析、图片分析、类型判断和综合判断流程，并保存结构化分析结果。
- Feed 与导出：支持单账号 Feed、聚合 Feed、文章导出任务和下载路径。
- 代理与限流：代理可按业务服务绑定，支持失败冷却、成功率、代理类型、轮换模式和策略配置。
- 日志与任务：保留抓取任务、操作日志、失败原因和运行统计，便于排查系统阻塞点。
- 单容器 Web 托管：生产镜像内置前端产物，后端支持前端路由刷新 fallback。

## 项目结构

```text
app/         FastAPI 应用、API 路由、服务层、仓储层、任务和模型
alembic/     PostgreSQL 数据库迁移链
frontend/    Vue 3、Vite、Element Plus、Pinia 管理后台
tests/       后端回归测试
docs/        部署、配置、设计和项目参考文档
```

## 技术栈

- 后端：FastAPI、SQLAlchemy Async、Alembic、Pydantic Settings、APScheduler
- 前端：Vue 3、Vite、Element Plus、Pinia、Vue Router、Axios
- 数据库：PostgreSQL
- 缓存与运行状态：Redis
- 部署：Dockerfile 多阶段构建、Docker Compose

## Docker 快速开始

推荐使用 Docker Compose 直接启动完整环境：

```bash
docker compose up -d --build
```

启动后访问：

- Web UI 和 API：<http://localhost:8000>
- 健康检查：<http://localhost:8000/health>
- API 文档：<http://localhost:8000/docs>

默认管理员：

- 用户名：`admin`
- 密码：`admin123`

生产环境暴露服务前必须修改 `JWT_SECRET_KEY`，并在首次登录后修改默认管理员密码。更多部署、升级、备份、恢复和日志查看方式见 [Docker 部署文档](docs/docker.md)。

## 本地开发

准备依赖：

- Python 3.12
- Node.js 20.19+ 或 22.12+
- PostgreSQL
- Redis

安装后端依赖：

```bash
uv sync
```

安装前端依赖：

```bash
cd frontend
npm install
```

复制本地环境变量：

```bash
cp .env.example .env
```

执行数据库迁移：

```bash
uv run alembic upgrade head
```

启动后端：

```bash
uv run uvicorn app.main:app --reload
```

启动前端开发服务器：

```bash
cd frontend
npm run dev
```

默认本地地址：

- 前端开发服务器：<http://localhost:5173>
- 后端 API：<http://localhost:8000>

## 配置

配置通过环境变量加载：

- `.env.example`：本地开发示例。
- `.env.docker.example`：Docker 部署覆盖示例。

关键配置包括 `DATABASE_URL`、`REDIS_URL`、`JWT_SECRET_KEY`、`MEDIA_ROOT`、`FRONTEND_DIST_PATH`、`LLM_API_URL`、`LLM_API_KEY`、`WEREAD_PLATFORM_URL` 和默认管理员启动配置。完整说明见 [配置文档](docs/configuration.md)。

## 测试

后端检查：

```bash
uv run ruff check app tests scripts
uv run pytest -q
uv run python -m compileall app tests scripts
```

前端构建：

```bash
cd frontend
npm run build
```

Docker 检查：

```bash
docker compose config
docker compose build
```

## 文档

- [技术设计文档](docs/technical-design.md)
- [Docker 部署](docs/docker.md)
- [配置说明](docs/configuration.md)
- [项目期望](docs/项目期望.md)
- [前端详情](docs/前端详情.md)
- [后端详情](docs/后端详情.md)
- [参考项目详情](docs/参考项目详情.md)

`external_references/` 是本地参考资料目录，已被 Git 和 Docker build context 排除，不属于开源发布内容。

## 贡献

提交 Pull Request 前请阅读 [CONTRIBUTING.md](CONTRIBUTING.md)。请保持变更聚焦，为后端行为、权限、迁移、Feed、导出和调度逻辑补充必要测试，不要提交运行数据、密钥、媒体文件、日志、前端构建产物或 `external_references/`。

## 安全

请不要在公开 issue 中披露漏洞细节、密钥、QR 会话、日志或个人数据。漏洞报告方式和部署安全建议见 [SECURITY.md](SECURITY.md)。

## 许可证

Just-We 使用 [MIT License](LICENSE)。
