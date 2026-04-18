# Just-We

面向微信公众号内容监测的前后端一体平台。

项目支持平台用户登录、抓取账号绑定、公众号监测源管理、自动调度抓取、文章图片本地化、AI 内容分析、账号健康检查和站内/邮件告警。当前代码已经清理掉旧的遗留页面与接口，只保留现行的 `collector_accounts + monitored_accounts` 主流程。

## 功能概览

- 平台用户登录与角色权限：`admin` / `operator` / `viewer`
- 抓取账号管理：
  - 公众号后台二维码登录
  - WeRead 外部平台二维码接入
  - 定时健康检查、失效检测、即将过期提醒
- 公众号监测：
  - 从文章链接解析 `biz` / `fakeid`
  - 为不同用户分别创建自己的监测对象
  - Tier 分层、抓取策略调整、手动触发抓取
- 抓取链路：
  - 自动调度活跃监测对象
  - 按 Tier 映射唯一抓取方式
  - 文章正文抓取、图片本地化保存
- AI 与告警：
  - 可配置外部 AI API
  - 高相关命中、连续低相关、抓取失败、账号失效等通知
  - SMTP 邮件外发
- 管理后台：
  - 仪表盘
  - 抓取账号页
  - 公众号监测页
  - 文章库与详情
  - 作业与审计日志
  - 代理管理
  - 系统设置

## 技术栈

- Backend: FastAPI, SQLAlchemy Async, Alembic, Redis, APScheduler
- Frontend: Vue 3, Vite, Element Plus, Pinia
- Database: PostgreSQL

## 项目结构

```text
app/         FastAPI 应用、模型、服务、任务
frontend/    Vue 3 管理后台
alembic/     数据库迁移
tests/       后端测试
docs/        需求与项目文档
```

## 快速开始

### 1. 准备环境

- Python `3.12+`
- Node.js `18+`
- PostgreSQL
- Redis

### 2. 配置环境变量

复制 `.env.example` 为 `.env`，至少确认以下配置：

```env
DATABASE_URL=postgresql+asyncpg://postgres:postgres@localhost:5432/dynamicwepubmonitor
REDIS_URL=redis://localhost:6379/0
JWT_SECRET_KEY=change-me-in-production
LLM_API_URL=https://api.example.com/v1/chat/completions
LLM_API_KEY=
LLM_MODEL=gpt-4o
WEREAD_PLATFORM_URL=
```

说明：

- `WEREAD_PLATFORM_URL` 为空时，WeRead 二维码登录不可用
- 公众号后台二维码登录不依赖该字段
- 邮件告警配置走系统设置页面保存，不依赖 `.env`

### 3. 安装依赖

后端：

```bash
uv sync
```

前端：

```bash
cd frontend
npm install
```

### 4. 初始化数据库

```bash
uv run alembic upgrade head
```

### 5. 启动服务

后端：

```bash
uv run uvicorn app.main:app --reload
```

前端：

```bash
cd frontend
npm run dev
```

默认前端地址：`http://localhost:5173`  
默认后端地址：`http://localhost:8000`

## 默认管理员

开发环境启动时，系统会自动确保存在默认管理员：

- 登录名：`admin`
- 邮箱：`admin@admin.com`
- 密码：`admin123`

可通过环境变量关闭或覆盖：

- `ENSURE_DEFAULT_ADMIN`
- `DEFAULT_ADMIN_ALIAS`
- `DEFAULT_ADMIN_EMAIL`
- `DEFAULT_ADMIN_PASSWORD`

## 测试与校验

后端测试：

```bash
pytest -q
```

前端构建校验：

```bash
cd frontend
npm run build
```

最近一次清理后的本地验证结果：

- `pytest -q`：`96 passed`
- `npm run build`：通过

## 当前保留的主流程

仓库已经移除以下历史遗留内容：

- 旧 `/api/accounts` 与 `/api/accounts/qr` 接口
- 未接入现行路由的旧前端账号页和旧 store/composable
- 无实际引用的图表、封装组件和模拟扫码页面

当前统一使用：

- `collector_accounts`：抓取账号
- `monitored_accounts`：监测对象
- `articles`：文章与 AI 结果

## 文档

`docs/` 目录只保留四份当前权威文档：

- [项目期望](docs/项目期望.md)
- [参考项目详情](docs/参考项目详情.md)
- [前端详情](docs/前端详情.md)
- [后端详情](docs/后端详情.md)

## 注意事项

- 项目当前以 PostgreSQL 为默认数据库，不再维护 SQLite 作为正式运行方案
- 前端构建仍会提示 `element-plus` 主包体积较大，这是打包优化问题，不影响运行
- 如果你要接通真实 WeRead 登录，需提供兼容平台接口
