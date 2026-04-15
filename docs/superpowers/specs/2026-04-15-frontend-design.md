# DynamicWePubMonitor 前端设计方案

## 1. 项目概述

**项目**: DynamicWePubMonitor 前端
**对应后端**: Python FastAPI + PostgreSQL/SQLite + Redis
**核心功能**: 微信公众号智能权重监控系统前端界面

## 2. 技术栈

| 类别 | 选择 | 说明 |
|------|------|------|
| 框架 | Vue3 (Composition API) | 现代化，响应式 |
| UI 库 | Element Plus | 按设计文档使用卡片式圆角组件 |
| 构建工具 | Vite | 快速开发，冷启动 |
| 状态管理 | Pinia | Vue3 官方推荐，轻量 |
| HTTP 客户端 | Axios | 功能丰富，拦截器支持 |
| CSS 方案 | SCSS + CSS Variables | 灵活，主题系统支持 |
| 实时通信 | SSE | 通知、日志流单向推送 |
| 图表 | Element Plus 内置图表 | 简化实现 |

## 3. 项目结构（功能模块化）

```
frontend/
├── public/
│   └── favicon.ico
├── src/
│   ├── api/                    # API 模块（按后端模块划分）
│   │   ├── auth.js             # 登录/注册/认证
│   │   ├── accounts.js         # 账号管理
│   │   ├── articles.js         # 文章管理
│   │   ├── proxies.js          # 代理管理
│   │   ├── weight.js           # 权重配置
│   │   ├── users.js            # 用户管理
│   │   ├── logs.js             # 日志
│   │   ├── notifications.js    # 通知
│   │   └── index.js            # Axios 实例配置
│   ├── assets/
│   │   ├── styles/             # 全局样式
│   │   │   ├── _variables.scss # CSS Variables（奶白色+橘红色主题）
│   │   │   ├── _base.scss      # 基础样式（圆角、阴影规范）
│   │   │   ├── _transitions.scss# 过渡动画
│   │   │   └── index.scss      # 入口文件
│   │   └── images/
│   │       └── logo.svg
│   ├── components/             # 全局公共组件
│   │   ├── layout/
│   │   │   ├── AppLayout.vue    # 主布局容器
│   │   │   ├── AppSidebar.vue   # 可收起侧边栏
│   │   │   └── AppHeader.vue    # 顶部导航
│   │   ├── common/
│   │   │   ├── StatCard.vue     # 指标卡片（数字+动画）
│   │   │   ├── StatusTag.vue    # 状态标签（Tier/状态）
│   │   │   ├── DataTable.vue    # 统一表格封装
│   │   │   ├── EmptyState.vue   # 空状态骨架屏
│   │   │   └── ConfirmModal.vue  # 确认弹窗
│   │   ├── auth/
│   │   │   └── ScanQRCode.vue   # 扫码登录弹窗
│   │   └── dashboard/
│   │       ├── TrendChart.vue    # 趋势图
│   │       ├── TierPieChart.vue  # Tier 分布饼图
│   │       └── RecentArticles.vue# 最近高相关文章
│   ├── composables/             # 组合式函数
│   │   ├── useAuth.js           # 认证逻辑
│   │   ├── useSSE.js            # SSE 实时通信
│   │   ├── usePermissions.js    # 权限判断
│   │   └── useCountUp.js        # 数字动画
│   ├── stores/                  # Pinia 状态管理
│   │   ├── auth.js              # 用户认证状态
│   │   ├── accounts.js          # 账号列表/筛选
│   │   ├── articles.js          # 文章列表/筛选
│   │   ├── notifications.js     # 通知列表
│   │   └── app.js               # 全局应用状态（侧边栏折叠等）
│   ├── router/
│   │   ├── index.js             # 路由配置
│   │   └── guards.js            # 路由守卫（权限控制）
│   ├── utils/
│   │   ├── request.js          # Axios 封装（拦截器）
│   │   └── format.js            # 格式化工具
│   ├── views/                   # 页面（功能模块化）
│   │   ├── auth/
│   │   │   ├── Login.vue        # 登录页
│   │   │   └── Register.vue      # 注册页
│   │   ├── dashboard/
│   │   │   └── Dashboard.vue    # 仪表盘
│   │   ├── accounts/
│   │   │   ├── AccountList.vue  # 账号列表（表格）
│   │   │   ├── AccountDetail.vue# 详情抽屉
│   │   │   └── AccountForm.vue  # 添加/编辑表单
│   │   ├── articles/
│   │   │   ├── ArticleList.vue  # 文章列表（表格）
│   │   │   └── ArticleDetail.vue # 文章详情
│   │   ├── proxies/
│   │   │   └── ProxyManage.vue  # 代理管理（Tab）
│   │   ├── weight/
│   │   │   └── WeightConfig.vue # 权重配置
│   │   ├── logs/
│   │   │   └── LogsMonitor.vue  # 日志与监控
│   │   ├── users/
│   │   │   └── UserManage.vue   # 用户管理
│   │   └── settings/
│   │       └── SystemSettings.vue# 系统设置
│   ├── App.vue
│   └── main.js
├── index.html
├── vite.config.js
├── package.json
└── .env.example
```

## 4. 设计系统

### 4.1 配色方案（CSS Variables）

```scss
// 奶白色主题
$color-bg: #F8F4F0;           // 主背景
$color-card: #FFFFFF;          // 卡片背景
$color-text: #333333;          // 主文字
$color-text-secondary: #666666;// 次要文字

// 橘红色点缀
$color-primary: #FF6B00;      // 主色
$color-primary-dark: #E55F00; // hover 状态
$color-danger: #FF3D00;        // 警告/高优

// 状态色
$color-success: #22C55E;      // 成功
$color-info: #3B82F6;         // 中性/信息
```

### 4.2 圆角与阴影规范

```scss
$radius-sm: 8px;   // 按钮、输入框
$radius-md: 16px;  // 卡片、面板
$radius-lg: 24px;  // 大卡片、Modal

$shadow-card: 0 4px 20px rgba(0, 0, 0, 0.06);
```

### 4.3 动画规范

```scss
$transition-fast: 0.15s ease;
$transition-normal: 0.25s ease;

// 卡片 hover 上浮
.card-hover {
  transition: transform $transition-normal, box-shadow $transition-normal;
  &:hover {
    transform: translateY(-4px) scale(1.02);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.1);
  }
}
```

## 5. 页面详细设计

### 5.1 登录/注册页 (/login, /register)

- **布局**: 全屏奶白色背景，居中大卡片（圆角 24px，宽 480px）
- **左侧 60%**: 奶白色渐变 + Logo + 标题 + 3 个特性小卡片
- **右侧**: Tab 切换登录/注册，圆形输入框，橘红色登录按钮
- **忘记密码**: 弹出圆角 Modal 输入邮箱重置

### 5.2 Dashboard (/dashboard)

- **顶部导航**: 右侧通知铃铛（未读红点）
- **指标卡片区**: 4 个横排卡片（总账号数、活跃任务、今日高相关文章、代理健康度）
- **中部**: 左侧 65% 趋势图，右侧 35% Tier 分布饼图
- **底部**: 最近高相关文章列表（5 条）
- **右下角**: 浮动"立即抓取"按钮（脉冲动画）

### 5.3 账号管理 (/accounts) - 表格视图

- **顶部**: 搜索栏 + 筛选（Tier、状态）
- **表格列**: 名称、biz、Tier（红 Tag）、Score（进度条）、最后抓取、下次间隔、状态、操作
- **操作按钮**: 手动抓取、Override、历史、删除
- **行点击**: 右侧滑出抽屉，含 90 天热力图、历史折线、Override 表单

### 5.4 代理管理 (/proxies) - 表格视图

- **顶部 Tab**: Polling / Fetch / Parse / AI
- **Tab 内容**: 3 个统计卡片 + 主表格
- **表格列**: IP:Port、类型、成功率、最后检查、状态（Tag）、操作
- **右侧**: 固定"添加代理"卡片

### 5.5 文章列表 (/articles) - 表格视图

- **顶部**: 搜索 + AI 占比滑块筛选
- **表格列**: 标题（+缩略图）、公众号、发布时间、AI 占比（标签）、来源、操作
- **标题点击**: 新标签页打开详情

### 5.6 文章详情 (/articles/:id)

- **左侧 70%**: 圆角卡片全文内容
- **右侧 30%**: 侧边栏（AI 判断 + reason + 图片列表）

### 5.7 权重配置 (/weight) - 仅管理员

- **左侧 40%**: Score 公式（纯文本/图片）+ 各因子解释
- **右侧 60%**: 可编辑表单（分组卡片：Tier 间隔、权重系数、阈值、惩罚规则）
- **底部**: "保存并重启调度" + "模拟测试"按钮
- **模拟区**: 输入历史数据 → 实时预览新 Score + Tier

### 5.8 日志与监控 (/logs) - 仅管理员

- **顶部 Tab**: 抓取日志 / 操作审计 / AI 调用日志
- **表格**: 时间、账号、事件、结果（色 Tag）、耗时、详情（展开 JSON）
- **右侧**: 实时日志流卡片（自动滚动）

### 5.9 用户管理 (/users) - 仅管理员

- **顶部统计**: 总账号数、WeRead/MP 账号数、即将到期数
- **Tab 1**: 系统用户表格（用户名、角色 Tag、最后登录、状态、操作）
- **Tab 2**: 公众号账号总览表格（名称+类型、biz、状态、到期时间、Tier&Score、操作）
- **到期警告**: 红色边框卡片，列出 30 天内到期账号
- **添加账号 Modal**: WeRead/MP Tab + 大二维码 + 扫码成功自动关闭

### 5.10 系统设置 (/settings) - 仅管理员

- **左侧菜单**: 通用配置 / AI Prompt / 通知渠道 / 数据清理 / 安全
- **右侧**: 对应子页表单卡片

## 6. 权限控制

| 角色 | 可访问页面 |
|------|-----------|
| operator / viewer | Dashboard、账号管理、代理管理、文章列表/详情、通知 |
| admin | 以上全部 + 权重配置、日志与监控、用户管理、系统设置 |

- **实现**: 路由守卫 + 后端 API 双重控制
- **受限页面**: 非 admin 访问时显示"仅管理员可见"提示卡片

## 7. 开发计划（渐进式）

### 第一阶段：基础建设
1. 项目脚手架（Vite + Vue3 + Element Plus + SCSS）
2. CSS Variables 主题系统
3. AppLayout 主布局组件
4. Axios 封装 + API 模块
5. Pinia stores 基础结构
6. 登录/注册页面 + JWT 认证流程

### 第二阶段：核心功能
1. Dashboard 仪表盘（StatCard + 图表 + 文章列表）
2. 账号管理页面（表格 + 筛选 + 详情抽屉）
3. 文章列表页面（表格 + 筛选）
4. 文章详情页面
5. SSE 通知中心

### 第三阶段：管理功能
1. 代理管理页面
2. 权重配置页面
3. 日志与监控页面
4. 用户管理页面
5. 系统设置页面

## 8. 技术调整说明

| 原设计 | 调整 | 原因 |
|--------|------|------|
| KaTeX 公式渲染 | 简化为纯文本/图片 | 降低复杂度，减少依赖 |
| ECharts | Element Plus 内置图表 | 与 Element Plus 更好集成 |

## 9. 验收标准

- [ ] 10 个页面全部实现
- [ ] 设计系统（奶白色+橘红色主题）全局一致
- [ ] 卡片 hover 动画、CountUp 数字动画正常
- [ ] RBAC 权限控制生效
- [ ] SSE 实时通知正常
- [ ] 表格筛选、搜索功能正常
- [ ] 扫码添加账号流程完整
- [ ] 响应式布局适配
