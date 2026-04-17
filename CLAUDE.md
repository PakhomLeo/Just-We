# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

**DynamicWePubMonitor** - 微信公众号智能权重监控系统

An intelligent WeChat public account monitoring system that dynamically adjusts monitoring priority (Tier 1-5) and fetch frequency (24h-336h) based on update frequency, AI-assessed content relevance (sports/events), and update stability.

**Core Value**: Solve the problem of "blind polling, wasted resources, easy blocking" in traditional public account monitoring. Enable high-value sports/event content to be discovered and pushed第一时间. Support team multi-user collaboration managing hundreds of public accounts.

**Target Users**: Teams monitoring sports/event-related WeChat public accounts who need automated, prioritized monitoring with AI-based content filtering.

### Tech Stack

| Layer | Technology |
|-------|------------|
| Backend | FastAPI + SQLAlchemy 2.0 Async + asyncpg + PostgreSQL 15+ |
| Frontend | Vue 3 (Composition API) + Vite + Element Plus + Pinia + ECharts |
| Task Scheduling | APScheduler + Redis |
| Authentication | JWT (python-jose + passlib[bcrypt]) |
| Database Migrations | Alembic |
| HTTP Client | httpx + curl_cffi (TLS fingerprint) |
| Validation | Pydantic v2 |
| Logging | loguru |

### Directory Structure

```
/Users/pakhom/code/
├── app/                          # Backend application
│   ├── main.py                   # FastAPI entry point with lifespan management
│   ├── __init__.py
│   ├── api/                      # FastAPI route handlers (routers)
│   │   ├── __init__.py           # Exports all routers
│   │   ├── auth.py               # /api/auth/* - Login, register, me
│   │   ├── accounts.py           # /api/accounts/* - Legacy account CRUD
│   │   ├── articles.py           # /api/articles/* - Article listing/detail
│   │   ├── collector_accounts.py # /api/collector-accounts/* - New fetch accounts
│   │   ├── monitored_accounts.py # /api/monitored-accounts/* - New monitored accounts
│   │   ├── fetch_jobs.py         # /api/fetch-jobs/* - Fetch job listing
│   │   ├── proxies.py            # /api/proxies/* - Proxy management
│   │   ├── qr.py                 # /api/accounts/qr/* - QR code login (legacy)
│   │   ├── system_config.py      # /api/system/* - AI config, fetch policy
│   │   ├── tasks.py              # /api/tasks/* - Manual fetch triggers
│   │   ├── users.py              # /api/users/* - User management (admin)
│   │   ├── weight.py             # /api/weight/* - Weight configuration
│   │   ├── logs.py               # /api/logs/* - Operation logs
│   │   └── notifications.py      # /api/notifications/* - Notifications
│   ├── core/                     # Core modules
│   │   ├── config.py             # Settings via pydantic-settings
│   │   ├── database.py           # Async SQLAlchemy session management
│   │   ├── dependencies.py       # Auth dependencies (get_current_user, require_role)
│   │   ├── exceptions.py         # Custom exceptions (AppException hierarchy)
│   │   └── redis.py              # Redis client + RedisKeys helper
│   ├── models/                   # SQLAlchemy ORM models
│   │   ├── base.py               # Base class + TimestampMixin
│   │   ├── user.py               # User (UUID, fastapi-users compatible)
│   │   ├── account.py            # Legacy Account (MonitoredAccount in new semantics)
│   │   ├── collector_account.py  # WeRead/MP Admin credential holder
│   │   ├── monitored_account.py  # New monitored public account entity
│   │   ├── article.py            # Article with AI judgment fields
│   │   ├── fetch_job.py          # Fetch pipeline execution record
│   │   ├── proxy.py              # Proxy pool with service_type
│   │   ├── notification.py       # Multi-target notification
│   │   ├── log.py                # OperationLog for audit trail
│   │   ├── system_config.py       # AIAnalysisConfig, FetchPolicy, NotificationEmailConfig
│   │   └── enum_utils.py         # value_enum() helper for PostgreSQL enums
│   ├── schemas/                   # Pydantic request/response models
│   │   ├── auth.py               # LoginRequest, RegisterRequest, Token, UserResponse
│   │   ├── account.py            # AccountCreate, AccountUpdate, AccountResponse
│   │   ├── article.py            # ArticleResponse, ArticleWithAccountResponse
│   │   ├── collector_account.py  # CollectorAccountResponse
│   │   ├── monitored_account.py  # MonitoredAccountCreate/Update/Response
│   │   ├── fetch_job.py          # FetchJobResponse
│   │   ├── proxy.py              # ProxyCreate/Update/Response
│   │   ├── qr.py                 # QRGenerateRequest/Response, QRStatusResponse
│   │   ├── weight.py             # WeightConfig, WeightConfigUpdate, WeightSimulateInput/Result
│   │   └── system_config.py      # AIConfigPayload, FetchPolicyPayload
│   ├── services/                  # Business logic layer
│   │   ├── auth_service.py       # JWT token creation/validation, user authentication
│   │   ├── account_service.py    # Legacy account CRUD + health check
│   │   ├── collector_account_service.py # Collector account visibility management
│   │   ├── monitoring_source_service.py # Monitored account CRUD + URL parsing
│   │   ├── article_service.py     # Article retrieval with visibility filtering
│   │   ├── proxy_service.py       # Proxy CRUD + health tracking
│   │   ├── fetcher_service.py     # Orchestrates WeReadFetcher/MpAdminFetcher
│   │   ├── fetch_pipeline_service.py # Full fetch pipeline
│   │   ├── fetch_job_service.py   # FetchJob listing
│   │   ├── ai_service.py          # LLM API integration for content analysis
│   │   ├── parser_service.py      # HTML cleaning + content extraction
│   │   ├── dynamic_weight_adjuster.py # Core weight/score/tier calculation
│   │   ├── scheduler_service.py    # APScheduler job management
│   │   ├── qr_login_service.py     # QR code state machine + mock login
│   │   ├── health_service.py       # Account/collector health check
│   │   ├── notification_service.py # Notification CRUD + alert triggers
│   │   ├── system_config_service.py # System config CRUD
│   │   └── bootstrap_service.py    # Default admin user creation
│   ├── repositories/              # Data access layer
│   │   ├── base.py
│   │   ├── account_repo.py       # Legacy account queries
│   │   ├── collector_account_repo.py
│   │   ├── monitored_account_repo.py
│   │   ├── article_repo.py       # Article queries with selectinload
│   │   ├── proxy_repo.py
│   │   ├── user_repo.py          # User by email/UUID
│   │   ├── log_repo.py           # OperationLog queries
│   │   ├── fetch_job_repo.py
│   │   └── system_config_repo.py
│   ├── tasks/                     # Background task entry points
│   │   ├── __init__.py
│   │   ├── fetch_task.py         # run_single_account(), run_all_accounts()
│   │   └── health_task.py        # run_all_collector_health_checks()
│   └── utils/                     # Utility functions
│       ├── proxy_rotator.py
│       ├── html_cleaner.py
│       ├── image_downloader.py
│       └── qr_code.py
├── frontend/                      # Frontend Vue 3 application
│   ├── src/
│   │   ├── main.js                # App entry point
│   │   ├── App.vue                # Root component
│   │   ├── api/                   # Axios API modules
│   │   │   ├── index.js           # Axios instance with interceptors
│   │   │   ├── auth.js            # Login/register/me
│   │   │   ├── accounts.js        # Account CRUD + QR code APIs
│   │   │   ├── articles.js
│   │   │   ├── collectorAccounts.js
│   │   │   ├── monitoredAccounts.js
│   │   │   ├── fetchJobs.js
│   │   │   ├── proxies.js
│   │   │   ├── system.js
│   │   │   ├── weight.js
│   │   │   ├── logs.js
│   │   │   ├── notifications.js
│   │   │   └── users.js
│   │   ├── assets/styles/
│   │   │   ├── _variables.scss    # CSS Variables (cream-orange theme)
│   │   │   ├── _base.scss         # Base styles, transitions
│   │   │   ├── _transitions.scss
│   │   │   └── index.scss
│   │   ├── components/
│   │   │   ├── layout/
│   │   │   │   ├── AppLayout.vue  # Main layout wrapper
│   │   │   │   ├── AppSidebar.vue # Navigation sidebar
│   │   │   │   └── AppHeader.vue  # Top bar with page title
│   │   │   ├── common/
│   │   │   │   ├── StatCard.vue   # Animated number card
│   │   │   │   ├── StatusTag.vue
│   │   │   │   ├── DataTable.vue   # Table wrapper
│   │   │   │   ├── EmptyState.vue
│   │   │   │   └── ConfirmModal.vue
│   │   │   ├── auth/
│   │   │   │   └── ScanQRCode.vue # QR scan component
│   │   │   └── dashboard/
│   │   │       ├── TrendChart.vue # ECharts trend line
│   │   │       ├── TierPieChart.vue # ECharts pie chart
│   │   │       └── RecentArticles.vue
│   │   ├── composables/
│   │   │   ├── useAuth.js         # Auth state and methods
│   │   │   ├── useSSE.js          # Server-Sent Events hook
│   │   │   ├── usePermissions.js  # Role-based access helpers
│   │   │   └── useCountUp.js      # Number animation
│   │   ├── stores/
│   │   │   ├── auth.js            # JWT token + user info
│   │   │   ├── accounts.js
│   │   │   ├── articles.js
│   │   │   ├── notifications.js
│   │   │   └── app.js
│   │   ├── router/
│   │   │   ├── index.js           # Vue Router with guards
│   │   │   └── guards.js          # Auth + admin guards
│   │   ├── utils/
│   │   │   └── request.js         # Axios wrapper with error handling
│   │   └── views/
│   │       ├── auth/
│   │       │   └── Login.vue      # Login/register form
│   │       ├── dashboard/
│   │       │   └── Dashboard.vue
│   │       ├── accounts/
│   │       │   ├── AccountList.vue    # Legacy (redirects to /mp-accounts)
│   │       │   ├── AccountDetail.vue
│   │       │   ├── AccountForm.vue
│   │       │   └── MpAccountManage.vue # Monitored account management
│   │       ├── articles/
│   │       │   ├── ArticleList.vue
│   │       │   └── ArticleDetail.vue
│   │       ├── users/
│   │       │   ├── UserManage.vue     # Capture accounts (QR login)
│   │       │   └── SystemUsers.vue    # System user CRUD (admin)
│   │       ├── proxies/
│   │       │   └── ProxyManage.vue
│   │       ├── weight/
│   │       │   └── WeightConfig.vue
│   │       ├── logs/
│   │       │   └── LogsMonitor.vue
│   │       └── settings/
│   │           └── SystemSettings.vue
│   ├── package.json
│   └── vite.config.js
├── alembic/                        # Database migrations
│   ├── env.py
│   ├── script.py.mako
│   └── versions/                   # Migration versions (0001-0008+)
├── tests/                          # Backend tests (81 passing)
│   ├── conftest.py                 # Fixtures for all models
│   ├── test_api.py
│   ├── test_services.py
│   ├── test_models.py
│   ├── test_weight.py
│   └── test_legacy_account_migration.py
├── docs/                           # Documentation
│   ├── MEMORY.md                   # Primary authoritative doc (Chinese)
│   ├── 项目完整文档.md              # Complete documentation (Chinese)
│   └── 目标需求文档.md              # Requirements document (Chinese)
├── pyproject.toml
├── alembic.ini
└── main.py                         # Alternative entry point
```

## Commands

### Backend

```bash
# Development server with hot reload
uv run uvicorn app.main:app --reload

# Run all tests
pytest -q

# Run tests with coverage report
pytest --cov=app tests/

# Run a specific test file
pytest tests/test_specific_file.py -q

# Run linting
ruff check app/
ruff format app/

# Format code only
black app/

# Type checking
mypy app/

# Database migrations (Alembic)
alembic upgrade head                           # Apply migrations
alembic revision --autogenerate -m "description"  # Create migration
alembic downgrade -1                           # Rollback one migration

# Initialize database (if not using migrations)
python -c "import asyncio; from app.core.database import init_db; asyncio.run(init_db())"

# Reset user password
python -c "
import asyncio
from passlib.context import CryptContext
from sqlalchemy import select
from app.core.database import get_db_context

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def reset():
    from app.models.user import User
    async with get_db_context() as db:
        result = await db.execute(select(User).where(User.email == 'admin@monitor.com'))
        user = result.scalars().first()
        user.hashed_password = pwd_context.hash('admin123')
        await db.commit()

asyncio.run(reset())
"
```

### Frontend

```bash
cd frontend

# Install dependencies
npm install

# Development server (proxies /api to localhost:8000)
npm run dev

# Production build
npm run build

# Preview production build locally
npm run preview

# Run unit tests
npm run test:unit

# Run e2e tests
npm run test:e2e
```

## Architecture

### Backend Layered Architecture

```
Request → API Router → Service → Repository → Database
                ↓
         Pydantic Schema (validation)
```

**Key Layers**:
- **API Layer** (`app/api/`): FastAPI routers handle HTTP requests/responses
- **Schema Layer** (`app/schemas/`): Pydantic models for request/response validation
- **Service Layer** (`app/services/`): Business logic, orchestration, and domain rules
- **Repository Layer** (`app/repositories/`): Data access abstraction (CRUD operations)
- **Model Layer** (`app/models/`): SQLAlchemy ORM models (database tables)

### Core Services

| Service | Responsibility |
|---------|---------------|
| `AuthService` | JWT token creation/validation, user authentication, last_login update |
| `AccountService` | Legacy account CRUD, manual override, health check coordination |
| `CollectorAccountService` | Collector account visibility management |
| `MonitoringSourceService` | Monitored account CRUD, URL parsing (create_from_url) |
| `ArticleService` | Article retrieval with visibility filtering by user role |
| `ProxyService` | Proxy CRUD, health tracking, get_proxy_for_service |
| `FetcherService` | Orchestrates WeReadFetcher/MpAdminFetcher, proxy selection |
| `FetchPipelineService` | Full pipeline: list → detail → parse → AI → save → weight update |
| `FetchJobService` | Recent FetchJob listing |
| `AIService` | LLM API integration for article content analysis |
| `ParserService` | HTML cleaning and content extraction |
| `DynamicWeightAdjuster` | Core algorithm: score = 0.35*Frequency + 0.25*Recency + 0.25*Relevance + 0.15*Stability |
| `SchedulerService` | APScheduler job management, load_account_schedules |
| `QRLoginService` | QR code state machine (generate/get_status/cancel/confirm/simulate) |
| `HealthService` | check_account_health, check_collector_account_health |
| `NotificationService` | Notification CRUD, alert triggers |
| `SystemConfigService` | System config CRUD (AIAnalysisConfig, FetchPolicy) |
| `BootstrapService` | ensure_default_admin on startup |

### Data Model (Core Entities)

```
User
├── id: UUID (primary key)
├── email: string (unique)
├── hashed_password: string
├── role: enum (admin, operator, viewer)
├── is_active: boolean
├── is_superuser: boolean
├── last_login: datetime (nullable)
└── timestamps (created_at, updated_at)

Account (Legacy - 旧语义)
├── id: int (primary key)
├── biz: string (unique, indexed) - WeChat biz identifier
├── fakeid: string (optional)
├── name: string
├── account_type: enum (weread, mp)
├── current_tier: int (1-5)
├── composite_score: float (0-100)
├── last_checked: datetime
├── last_updated: datetime
├── update_history: JSON
├── ai_relevance_history: JSON
├── manual_override: JSON (nullable)
├── cookies: JSON (nullable)
├── cookies_expire_at: datetime (nullable)
├── status: enum (active, inactive, blocked)
├── health_status: enum (normal, restricted, expired, invalid)
├── health_reason: string (nullable)
├── last_health_check: datetime (nullable)
└── timestamps

CollectorAccount (抓取账号 - 新语义)
├── id: int (primary key)
├── owner_user_id: UUID (FK → User)
├── account_type: enum (weread, mp_admin)
├── display_name: string
├── external_id: string (nullable)
├── credentials: JSON (token, cookies, etc.)
├── status: enum (active, disabled, expired, error)
├── health_status: enum (normal, restricted, expired, invalid)
├── risk_status: enum (normal, cooling, blocked)
├── risk_reason: string (nullable)
├── expires_at: datetime (nullable)
├── last_health_check: datetime (nullable)
├── last_success_at: datetime (nullable)
├── last_failure_at: datetime (nullable)
├── metadata_json: JSON (nullable)
└── timestamps

MonitoredAccount (监测公众号 - 新语义)
├── id: int (primary key)
├── owner_user_id: UUID (FK → User)
├── biz: string (unique, indexed)
├── fakeid: string (nullable)
├── name: string
├── source_url: text
├── avatar_url: text (nullable)
├── current_tier: int (1-5, higher = lower priority)
├── composite_score: float (0-100)
├── primary_fetch_mode: enum (weread, mp_admin)
├── fallback_fetch_mode: enum (weread, mp_admin)
├── status: enum (monitoring, paused, risk_observed, invalid)
├── last_polled_at: datetime (nullable)
├── last_published_at: datetime (nullable)
├── next_scheduled_at: datetime (nullable)
├── update_history: JSON
├── ai_relevance_history: JSON
├── manual_override: JSON (nullable)
├── strategy_config: JSON (nullable)
└── timestamps

Article
├── id: int (primary key)
├── account_id: int (FK → Account, legacy, nullable)
├── monitored_account_id: int (FK → MonitoredAccount, nullable)
├── title: string
├── content: text (cleaned)
├── raw_content: text
├── images: JSON (list of image URLs)
├── cover_image: text (nullable)
├── url: text (unique)
├── author: string (nullable)
├── published_at: datetime (nullable)
├── ai_relevance_ratio: float
├── ai_judgment: JSON (AI analysis result)
├── fetch_mode: string
├── content_fingerprint: string (SHA256)
├── source_payload: JSON
└── timestamps

Proxy
├── id: int (primary key)
├── host: string
├── port: int
├── username: string (nullable)
├── password: string (nullable)
├── service_type: enum (polling, fetch, parse, ai, weread_list, weread_detail, mp_list, mp_detail, generic)
├── success_rate: float
├── is_active: boolean
├── last_check_at: datetime (nullable)
├── success_count: int
├── failure_count: int
└── timestamps

FetchJob
├── id: int (primary key)
├── job_type: enum (full_sync, update_list, article_detail)
├── status: enum (pending, running, success, failed)
├── monitored_account_id: int (FK → MonitoredAccount)
├── collector_account_id: int (FK → CollectorAccount, nullable)
├── proxy_id: int (FK → Proxy, nullable)
├── fetch_mode: string (nullable)
├── error: text (nullable)
├── started_at: datetime
├── finished_at: datetime (nullable)
├── payload: JSON
└── timestamps

Notification
├── id: int (primary key)
├── owner_user_id: UUID (FK → User)
├── account_id: int (FK → Account, nullable)
├── collector_account_id: int (FK → CollectorAccount, nullable)
├── monitored_account_id: int (FK → MonitoredAccount, nullable)
├── article_id: int (FK → Article, nullable)
├── notification_type: string
├── title: string
├── content: string
├── is_read: boolean
├── payload: JSON (nullable)
└── timestamps

OperationLog
├── id: int (primary key)
├── user_id: UUID (FK → User, nullable)
├── action: string
├── target_type: string
├── target_id: int
├── before_state: JSON (nullable)
├── after_state: JSON (nullable)
├── detail: string (nullable)
└── timestamps

AIAnalysisConfig (System Config)
├── id: int (primary key)
├── api_url: string
├── api_key: string
├── model: string
├── prompt_template: text (nullable)
├── enabled: boolean
└── timestamps

FetchPolicy (System Config)
├── id: int (primary key)
├── tier_thresholds: JSON
├── check_intervals: JSON
├── primary_modes: JSON
├── retry_limit: int
├── retry_backoff_seconds: int
├── random_delay_min_ms: int
├── random_delay_max_ms: int
└── timestamps
```

### Fetch Pipeline Flow

```
1. Scheduler triggers fetch task (based on tier interval)
       ↓
2. FetchPipelineService.run_monitored_account(account_id)
       ↓
3. Select collector account (primary → fallback)
       ↓
4. UPDATE_LIST stage:
   - FetcherService calls WeReadFetcher or MpAdminFetcher
   - Returns list of ArticleUpdate (title, url, published_at, source_payload)
       ↓
5. Filter duplicates (by URL) and existing articles
       ↓
6. ARTICLE_DETAIL stage (per article):
   - Fetch raw HTML
   - Extract metadata (title, author, cover_image, published_at)
       ↓
7. Parse content (HTML → clean text)
       ↓
8. AI Analysis (AIService.analyze_article)
   - Returns relevance ratio, keywords, judgment
       ↓
9. Save article (ArticleService)
       ↓
10. Update weights:
    - DynamicWeightAdjuster.update_after_fetch()
    - Updates MonitoredAccount.tier, composite_score, update_history
       ↓
11. Update collector health (CollectorAccountService)
       ↓
12. Write FetchJob record
```

### Frontend Architecture

**Pinia Stores**:
- `auth` - Authentication state, JWT token, user info
- `accounts` - Account management state
- `articles` - Articles state
- `notifications` - Notification state
- `app` - Global app state

**Router Guards** (`router/index.js`, `router/guards.js`):
- `requiresAuth` meta: Redirects to `/login` if not authenticated
- `requiresAdmin` meta: Redirects to `/dashboard` if not admin role

**API Request Flow** (`utils/request.js`):
```
Axios Request → Interceptor adds Bearer token → API endpoint
                    ↓
              Response Interceptor:
              - 401 → logout + redirect to /login
              - Other errors → ElMessage.error
```

**Route Configuration**:

| Route | Page | Permission | Description |
|-------|------|------------|-------------|
| `/login` | Login.vue | Public | Login/register form |
| `/dashboard` | Dashboard.vue | Auth | Main dashboard with stats, charts |
| `/mp-accounts` | MpAccountManage.vue | Auth | Monitored accounts table |
| `/articles` | ArticleList.vue | Auth | Article listing with filters |
| `/articles/:id` | ArticleDetail.vue | Auth | Article content + AI judgment |
| `/proxies` | ProxyManage.vue | Auth | Proxy management with tabs |
| `/weight` | WeightConfig.vue | Admin | Weight formula + simulation |
| `/logs` | LogsMonitor.vue | Admin | Fetch logs with SSE stream |
| `/capture-accounts` | UserManage.vue | Auth | Collector accounts with QR login |
| `/system-users` | SystemUsers.vue | Admin | System user CRUD |
| `/settings` | SystemSettings.vue | Admin | System configuration |
| `/accounts` | AccountList.vue | Auth | Legacy, redirects to /mp-accounts |

### Design System

**Color Palette (Cream-Orange Theme)**:
```scss
$color-bg: #F8F4F0;              // Main background
$color-card: #FFFFFF;             // Card background
$color-text: #333333;            // Primary text
$color-text-secondary: #666666;   // Secondary text
$color-primary: #FF6B00;         // Primary (orange)
$color-primary-dark: #E55F00;     // Hover state
$color-danger: #FF3D00;          // Warning/high priority
$color-success: #22C55E;         // Success
$color-info: #3B82F6;            // Neutral/info
```

**Border Radius & Shadows**:
```scss
$radius-sm: 8px;    // Buttons, inputs
$radius-md: 16px;   // Cards, panels
$radius-lg: 24px;   // Large cards, Modals
$shadow-card: 0 4px 20px rgba(0, 0, 0, 0.06);
```

**Animations**:
```scss
$transition-fast: 0.15s ease;
$transition-normal: 0.25s ease;
```

## Configuration

### Environment Variables (`.env`)

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://postgres:postgres@localhost:5432/dynamicwepubmonitor` | PostgreSQL connection |
| `REDIS_URL` | `redis://localhost:6379/0` | Redis connection |
| `JWT_SECRET_KEY` | `change-me-in-production` | JWT signing key |
| `JWT_ALGORITHM` | `HS256` | JWT algorithm |
| `JWT_ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Token expiration |
| `LLM_API_URL` | `https://api.example.com/v1/chat/completions` | LLM API endpoint |
| `LLM_API_KEY` | `` | LLM API key |
| `LLM_MODEL` | `gpt-4o` | LLM model name |
| `DEBUG` | `True` | Debug mode |

### Weight/Tier Configuration

**Tier Thresholds and Check Intervals**:

| Tier | Score Threshold | Check Interval | Primary Mode |
|------|----------------|---------------|-------------|
| 1 | ≥ 80 | 24 hours | WeRead |
| 2 | ≥ 65 | 48 hours | WeRead |
| 3 | ≥ 50 | 72 hours | MP Admin |
| 4 | ≥ 35 | 144 hours | MP Admin |
| 5 | < 35 | 336 hours | MP Admin |

**Weight Calculation Formula**:
```
Score = 0.35×Frequency + 0.25×Recency + 0.25×Relevance + 0.15×Stability
```

**Factor Details**:
- **Frequency** (0.35): Updates in last 90 days + density. Burst accounts (+5 articles at once) get +15 points
- **Recency** (0.25): Time since last update + burst bonus. 30+ days silent then 3+ articles = +35 points
- **Relevance** (0.25): AI-assessed sports/event relevance ratio. <50% deducts 15-20 points
- **Stability** (0.15): Update variance tolerance. Burst+silent patterns score higher

**Manual Override**:
```json
{
  "target_tier": 3,
  "expire_at": "2026-04-20T00:00:00Z",
  "reason": "Manual emergency monitoring"
}
```

## API Endpoints

All API routes are prefixed with `/api`.

### Authentication (`/api/auth`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/login` | Login with email/password, returns JWT |
| POST | `/register` | Register new user |
| GET | `/me` | Get current user info |

### Legacy Accounts (`/api/accounts`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List accounts (paginated) |
| POST | `/` | Create account (manual biz) |
| GET | `/{id}` | Get account details |
| PUT | `/{id}` | Update account |
| DELETE | `/{id}` | Delete account |
| POST | `/{id}/override` | Manual tier/score override |
| DELETE | `/{id}/override` | Remove override |
| GET | `/{id}/history` | Historical changes |
| POST | `/{id}/crawl` | Manual crawl trigger |
| POST | `/{id}/health-check` | Health check |
| POST | `/batch-health-check` | Batch health check |

### QR Code Login (`/api/accounts/qr`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/generate` | Generate QR code |
| GET | `/status` | Poll scan status |
| DELETE | `/{ticket}` | Cancel login |
| POST | `/simulate/scan` | Simulate scan (dev) |
| POST | `/simulate/confirm` | Simulate confirm (dev) |

### Collector Accounts (`/api/collector-accounts`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List collector accounts |
| POST | `/qr/generate` | Generate QR code |
| GET | `/qr/status` | Poll QR status |
| DELETE | `/qr/{ticket}` | Cancel QR login |
| POST | `/qr/confirm` | Confirm QR scan |
| POST | `/qr/simulate-scan` | Simulate scan (dev) |
| POST | `/qr/simulate-confirm` | Simulate confirm (dev) |
| POST | `/{id}/health-check` | Health check |
| DELETE | `/{id}` | Delete collector account |

### Monitored Accounts (`/api/monitored-accounts`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List monitored accounts |
| POST | `/` | Create monitored account |
| GET | `/{id}` | Get monitored account |
| PUT | `/{id}` | Update monitored account |
| DELETE | `/{id}` | Delete monitored account |
| POST | `/{id}/fetch` | Manual fetch trigger |

### Fetch Jobs (`/api/fetch-jobs`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List recent fetch jobs |
| GET | `/{id}` | Get fetch job details |

### Articles (`/api/articles`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List articles (paginated, filterable) |
| GET | `/{id}` | Get article details |
| GET | `/account/{account_id}` | Articles by legacy account |
| GET | `/monitored/{monitored_account_id}` | Articles by monitored account |

### Proxies (`/api/proxies`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List proxies |
| POST | `/` | Create proxy |
| PUT | `/{id}` | Update proxy |
| DELETE | `/{id}` | Delete proxy |
| POST | `/{id}/test` | Test proxy |
| GET | `/stats` | Proxy statistics |

### System Config (`/api/system`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/ai-config` | Get AI configuration |
| PUT | `/ai-config` | Update AI configuration |
| GET | `/fetch-policy` | Get fetch policy |
| PUT | `/fetch-policy` | Update fetch policy |
| GET | `/notification-email` | Get email config |
| PUT | `/notification-email` | Update email config |

### Weight (`/api/weight`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/config` | Get weight configuration |
| PUT | `/config` | Update weight configuration (admin) |
| POST | `/simulate` | Simulate score calculation |

### Tasks (`/api/tasks`)

| Method | Path | Description |
|--------|------|-------------|
| POST | `/fetch/{account_id}` | Manual fetch for account |
| POST | `/fetch/all` | Fetch all accounts |
| GET | `/fetch/{account_id}/status` | Fetch status |

### Users (`/api/users`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List system users (admin) |
| POST | `/` | Create user (admin) |
| GET | `/{user_id}` | Get user details |
| PUT | `/{user_id}` | Update user |
| DELETE | `/{user_id}` | Delete user (admin) |

### Logs (`/api/logs`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List operation logs (admin) |
| GET | `/account/{account_id}` | Logs for account |

### Notifications (`/api/notifications`)

| Method | Path | Description |
|--------|------|-------------|
| GET | `/` | List notifications |
| PUT | `/{id}/read` | Mark as read |
| PUT | `/read-all` | Mark all as read |
| DELETE | `/{id}` | Delete notification |

## Database

- **Engine**: PostgreSQL 15+ with async SQLAlchemy 2.0
- **Connection**: Uses `asyncpg` driver
- **ORM Features**: Mapped columns, relationships, JSON columns
- **Migrations**: Alembic with autogenerate support (8 migrations exist)
- **Session Management**: `get_db()` dependency provides session per request, auto-commit on success, auto-rollback on exception

### Base Model

All models inherit from `Base` (DeclarativeBase) and use `TimestampMixin` which provides:
- `id`: Auto-incrementing integer primary key
- `created_at`: Server-set timestamp
- `updated_at`: Auto-updated timestamp

### Enum Handling

Enums use `value_enum()` wrapper to store enum values as strings in the database (not integer ordinals). PostgreSQL enums are case-sensitive.

### Field Aliases

Backend models use `current_tier` and `composite_score`, but API responses expose `tier` and `score` via `@computed_field` aliases in Pydantic schemas for frontend compatibility.

## Error Handling & Debugging

### Common Issues

**API 400 Bad Request**:
- Check if enum values match expected case (PostgreSQL enums are case-sensitive)
- Verify `owner_user_id` is passed as UUID string, not integer

**Relationship Not Loaded**:
- Use `selectinload(Model.relationship)` to preload related objects
- SQLAlchemy async doesn't auto-load relationships

**QR Code State Machine**:
- QR codes stored in Redis with 180s expiry
- Poll `GET /api/accounts/qr/status?ticket=xxx` every 2 seconds
- Status: `waiting` → `scanned` → `confirmed` | `expired`

### Debug Commands

```bash
# Check if services are running
lsof -ti:8000    # Backend
lsof -ti:6379    # Redis

# Restart backend
pkill -f "uvicorn app.main:app"
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000 &

# Test API with curl
TOKEN=$(curl -s -X POST "http://localhost:8000/api/auth/login" \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@monitor.com","password":"admin123"}' \
  | jq -r '.access_token')

curl -X GET "http://localhost:8000/api/users/" \
  -H "Authorization: Bearer $TOKEN"
```

## Development State

**Current Phase**: Post-refactoring - "Target state skeleton established, real fetching details and data migration not yet completed."

### Completed

- Backend new model主干 (CollectorAccount, MonitoredAccount, FetchJob, AIAnalysisConfig, FetchPolicy)
- New API主干 (collector-accounts, monitored-accounts, fetch-jobs, system/*)
- New fetch pipeline主干 (FetchPipelineService with WeReadFetcher/MpAdminFetcher)
- Frontend pages switched to new interfaces
- Alembic infrastructure with 8 migrations
- 81 passing tests with backward-compatible wrappers

### In Progress / Remaining

- Old `accounts` data migration to new `collector_accounts`/`monitored_accounts` tables
- Real WeRead/MP fetch details (currently has structure + mock-safe fallbacks)
- Anti-crawler, rate limiting, and circuit breaker policies
- Complete old endpoint/frontend cleanup
- Log center expansion from "recent tasks" to filterable fetch event center

### Legacy → New Mapping

| Old (Single Account) | New Split |
|---------------------|-----------|
| `Account` (mixed) | `CollectorAccount` (credentials) + `MonitoredAccount` (monitoring target) |
| `Account.account_type` | `CollectorAccount.account_type` or `MonitoredAccount.primary_fetch_mode` |
| `Account.cookies` | `CollectorAccount.credentials` |
| `Account.biz` | `MonitoredAccount.biz` |

**Compatibility**: Old API endpoints (`/accounts`, `/qr`) still exist for compatibility. `FetcherService.fetch_new_articles()` provides backward-compatible wrapper for legacy tests.

## Test Data

### Test Users

| Email | Password | Role |
|-------|----------|------|
| admin@monitor.com | admin123 | admin |
| operator@monitor.com | password123 | operator |
| viewer@monitor.com | password123 | viewer |

### Test Accounts (Legacy)

| Name | Type | Tier | Score |
|------|------|------|-------|
| 科技每日推送 | mp | 1 | 85.5 |
| 财经观察 | mp | 2 | 72.3 |
| 娱乐星闻 | mp | 3 | 65.0 |
| 体育世界 | mp | 4 | 45.2 |
| 汽车资讯 | mp | 5 | 28.0 |
| 读书笔记 | weread | 2 | 78.0 |
| 每周书单 | weread | 3 | 62.5 |
| 阅读时光 | weread | 4 | 40.0 |

## Key Files Reference

| Category | Key Files |
|----------|-----------|
| Backend entry | `app/main.py` |
| Auth | `app/services/auth_service.py`, `app/core/dependencies.py` |
| Database | `app/core/database.py`, `app/models/base.py` |
| Fetching | `app/services/fetcher_service.py`, `app/services/fetch_pipeline_service.py` |
| Weight algorithm | `app/services/dynamic_weight_adjuster.py` |
| QR login | `app/services/qr_login_service.py` |
| Frontend router | `frontend/src/router/index.js`, `frontend/src/router/guards.js` |
| API layer | `frontend/src/utils/request.js`, `frontend/src/api/index.js` |
| Auth store | `frontend/src/stores/auth.js` |
| Main layout | `frontend/src/components/layout/AppLayout.vue` |

## See Also

- `docs/MEMORY.md` - Primary authoritative documentation (Chinese)
- `docs/项目完整文档.md` - Complete project documentation (Chinese)
- `docs/目标需求文档.md` - Requirements document (Chinese)
