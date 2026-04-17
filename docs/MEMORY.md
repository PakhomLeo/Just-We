# DynamicWePubMonitor Memory

**最后更新**: 2026-04-16

## 0. 本次续开发记录

- 已新增 Alembic revision：`20260416_0002_legacy_account_data_migration.py`
- 该迁移会把旧 `accounts` 数据回填到：
  - `monitored_accounts`
  - `collector_accounts`
  - `articles.monitored_account_id`
- 当前迁移规则：
  - 旧 `Account` 默认迁入 `MonitoredAccount`
  - 旧 `Account` 只要存在凭证或可识别外部标识，就补建 `CollectorAccount`
  - 由于旧表没有归属用户字段，迁移会自动选择一个默认平台用户承接历史数据：
    - 优先管理员
    - 其次激活用户
    - 最后任意最早用户
- 已补最小测试覆盖迁移辅助映射规则
- 已推进抓取器第二阶段实现：
  - `MpAdminFetcher` 已支持分页抓取更新列表
  - 单次抓取已对列表 URL 去重
  - 详情抓取已补充微信公众号页面结构化元数据提取：
    - 标题
    - 作者
    - 封面
    - 发布时间
  - `FetchPipelineService` 已在抓详情前按 URL 做增量过滤，避免重复抓取已存在文章
- 已补定向测试覆盖：
  - MP 后台分页与去重
  - 文章详情元数据提取
  - pipeline URL 增量过滤
- 已补抓取失败分类第一版：
  - 当前统一分类为：
    - `configuration_error`
    - `credentials_invalid`
    - `risk_control`
    - `temporary_failure`
  - `FetchFailedException` 已携带分类与是否可重试信息
  - `FetchPipelineService` 已把失败分类写入 `FetchJob.payload`
  - `CollectorAccountService` 已按失败分类更新抓取账号健康/风控状态
- 已推进 `WeReadFetcher` 第一版真实链路：
  - 已支持根据 `source_url` / `biz` / `fakeid` 推导公众号历史页 URL
  - 已支持解析公开页 HTML 中嵌入的：
    - `msgList`
    - `general_msg_list`
  - 已支持从嵌入 JSON 中提取：
    - 主文章
    - 多图文子文章
  - 当嵌入 JSON 不可用时，会回退到页面锚点链接提取
- 已细化抓取任务记录：
  - 一个监测源执行一次完整抓取时，当前会生成：
    - `FULL_SYNC`
    - `UPDATE_LIST`
    - `ARTICLE_DETAIL`
  - 详情任务会在 `payload` 中记录文章 URL / 标题
  - 列表任务和详情任务失败时，都会各自写入失败分类和 `retryable`
- 已补运行期兼容性迁移与联调修复：
  - 新增 Alembic revisions：
    - `20260416_0003_normalize_user_role_enum.py`
    - `20260416_0004_normalize_legacy_account_enums.py`
    - `20260416_0005_normalize_proxy_and_health_status.py`
  - 已把测试库中的旧大写枚举 / 状态值统一到当前模型使用的小写语义：
    - `users.role`
    - `accounts.account_type`
    - `accounts.status`
    - `accounts.health_status`
    - `proxies.service_type`
  - 已修复新接口响应 schema 中 `owner_user_id` 与数据库 `UUID` 类型不匹配导致的 500
  - 已在真实测试库上完成 smoke check：
    - `auth/me`
    - `accounts`
    - `articles`
    - `collector-accounts`
    - `monitored-accounts`
    - `fetch-jobs`
    - `proxies`
    - `logs`
    - `users`
  - 当前前后端均可正常启动，且核心页面依赖接口已可返回成功响应
- 下一步应做的仍然是：
  - 在另一份更接近生产的旧 PostgreSQL 样本库上再跑一次迁移验证
  - 核对 owner 归属策略是否符合实际业务
  - 验证文章映射是否与旧 `accounts.id -> monitored_accounts.id` 预期一致
  - 继续把前端从旧 `/accounts` 语义完全迁移到 `collector-accounts` / `monitored-accounts`

## 1. 当前阶段结论

项目已经从“单一 `Account` 同时表示抓取账号和监测公众号”的旧语义，推进到“抓取账号 / 监测公众号 / 抓取任务 / 系统配置”分层的目标态主干。

这次重构已经完成了：

- 后端新模型主干
- 新 API 主干
- 新抓取流水线主干
- 抓取账号页与公众号监测页的新接口接线
- 系统设置页和日志页的新接口接线
- Alembic 基础设施和首个目标态迁移文件

当前代码已经能通过后端测试和前端构建，但仍处在“目标态主骨架已建立、真实抓取细节和数据迁移尚未完成”的阶段。

## 2. 本次已完成内容

### 2.1 后端数据模型重构

新增了以下核心模型：

- `CollectorAccount`
  - 代表抓取账号
  - 类型：`weread` / `mp_admin`
  - 包含归属用户、凭证、健康状态、过期时间、风险状态
- `MonitoredAccount`
  - 代表被监测公众号
  - 包含 `biz`、`fakeid`、名称、来源链接、tier、score、主抓取通道、备用通道、调度字段
- `FetchJob`
  - 记录抓取流水线执行情况
- `AIAnalysisConfig`
  - 系统级 AI 配置
- `FetchPolicy`
  - 系统级抓取与 tier 策略

同时扩展了：

- `Article`
  - 增加 `monitored_account_id`
  - 增加 `cover_image`
  - 增加 `author`
  - 增加 `fetch_mode`
  - 增加 `content_fingerprint`
  - 增加 `source_payload`
- `Proxy.ServiceType`
  - 增加 `weread_list`
  - 增加 `weread_detail`
  - 增加 `mp_list`
  - 增加 `mp_detail`

### 2.2 后端 API 重组

新增主接口：

- `/api/collector-accounts/*`
- `/api/monitored-accounts/*`
- `/api/fetch-jobs/*`
- `/api/system/ai-config`
- `/api/system/fetch-policy`

当前接口职责：

- `collector-accounts`
  - 抓取账号列表
  - 扫码生成
  - 扫码状态轮询
  - 模拟扫码 / 模拟确认
  - 删除
  - 健康检查
- `monitored-accounts`
  - 通过文章链接创建监测源
  - 列表 / 详情 / 更新
  - 手动触发抓取
- `fetch-jobs`
  - 返回最近抓取任务
- `system`
  - 读写系统级 AI 配置
  - 读写抓取策略配置

旧接口当前仍保留，用于兼容原页面和原测试，但新主流程已经不再依赖旧 `/accounts` 语义。

### 2.3 后端服务重构

新增或重做的服务：

- `CollectorAccountService`
- `MonitoringSourceService`
- `FetchJobService`
- `SystemConfigService`
- `FetchPipelineService`

已调整的服务：

- `QRLoginService`
  - 现在只负责扫码状态机和创建 `CollectorAccount`
  - 不再直接创建公众号监测对象
- `FetcherService`
  - 已改成统一编排器
  - 内部拆出 `WeReadFetcher` 和 `MpAdminFetcher`
  - 保留了旧 `fetch_new_articles` 兼容入口，确保旧测试继续通过
- `AIService`
  - 可从数据库读取系统级 AI 配置
  - 默认不再以 mock 为主
- `SchedulerService`
  - 已切换为面向 `MonitoredAccount`
- `tasks/fetch_task.py`
  - 已切换为面向监测公众号运行

### 2.4 新抓取主流程

当前抓取主流程是：

1. 从 `MonitoredAccount` 开始
2. 根据主抓取通道和账号可用性选择 `CollectorAccount`
3. 根据抓取通道选择代理
4. 拉更新列表
5. 逐篇抓详情
6. 解析 HTML
7. 调用 AI 分析
8. 保存文章
9. 更新 tier / score / 历史
10. 写入 `FetchJob`

这是目标态主链路的第一版可运行骨架。

### 2.5 前端已切换页面

已明显切换到新接口 / 新语义的页面：

- `frontend/src/views/users/UserManage.vue`
  - 作为抓取账号页
  - 现在使用 `collector-accounts`
- `frontend/src/views/accounts/MpAccountManage.vue`
  - 作为公众号监测页
  - 现在使用 `monitored-accounts`
- `frontend/src/views/settings/SystemSettings.vue`
  - 现在读写 `system/ai-config` 和 `system/fetch-policy`
- `frontend/src/views/logs/LogsMonitor.vue`
  - 现在显示 `fetch-jobs`

新增前端 API 模块：

- `frontend/src/api/collectorAccounts.js`
- `frontend/src/api/monitoredAccounts.js`
- `frontend/src/api/system.js`
- `frontend/src/api/fetchJobs.js`

### 2.6 Alembic

已补齐：

- `alembic/env.py`
- `alembic/script.py.mako`
- `alembic/versions/20260416_0001_target_state_init.py`

当前状态：

- Alembic 结构已能用
- 已有目标态初始化迁移
- 但还没有“旧数据搬迁逻辑”

## 3. 当前验证状态

本轮重构完成后已验证：

- `pytest -q` -> `81 passed`
- `python3 -m compileall /Users/pakhom/code/app` -> 通过
- `npm run build` in `/Users/pakhom/code/frontend` -> 通过

说明：

- 后端测试当前仍主要覆盖旧服务和基础逻辑
- 由于保留了兼容入口，现有测试没有被这次重构打断
- 但这不等于新抓取链路已经达到生产可用

## 4. 当前真实状态

当前需要明确几个事实：

### 4.1 已完成的是“目标态骨架”，不是最终生产版本

已完成：

- 语义拆分
- 模型拆分
- 接口拆分
- 页面主入口拆分
- 流水线主干

尚未完成：

- 旧 `accounts` 数据向新表的正式迁移
- 参考项目级别的真实微信读书抓取细节
- 参考项目级别的真实公众号后台抓取细节
- 更强的反爬、限速、熔断、恢复策略
- 旧接口和旧页面的彻底下线

### 4.2 真实抓取链路目前是“可接结构 + 部分真实调用 + 安全回退”

含义：

- 不是纯 mock
- 也不是完整复刻参考项目能力
- 现在的实现重点是把架构搭对，把接口和状态流先统一起来

### 4.3 数据库层仍是“可创建 + 可迁移初始化”，但不是“生产迁移完成”

当前代码：

- 应用启动仍通过 `create_all` 创建表
- Alembic 已经补上
- 但数据库实际升级流程还没打通到“旧库平滑迁移”

## 5. 下一步优先事项

下一步最应该继续做的事有两项，优先级顺序如下。

### 优先级 1：写正式数据迁移逻辑

目标：

- 将旧 `accounts` 中的数据迁入 `collector_accounts`
- 将旧监测公众号数据迁入 `monitored_accounts`
- 将 `articles.account_id` 对应关系映射到 `articles.monitored_account_id`

需要做的事情：

- 新增一版“数据搬迁迁移”而不是仅建表迁移
- 明确旧 `accounts` 中哪些记录属于抓取账号，哪些属于监测公众号
- 生成稳妥的迁移规则
- 迁移完成后验证：
  - 账号归属正确
  - 监测源关联正确
  - 文章关联正确

原因：

- 不做这一步，当前目标态只能在“新库/空库”上最顺畅
- 这一步决定重构是否真正可落地

### 优先级 2：深化真实抓取器实现

目标：

- 将现在的抓取适配器从“结构正确”推进到“真实可用”

需要做的事情：

- 微信读书通道：
  - 明确参考 `wewe-rss` 的真实请求链路
  - 接入真实凭证字段
  - 完成更新列表获取和增量识别
- 公众号后台通道：
  - 明确参考 `wechat-download-api` / `we-mp-rss` 的真实请求链路
  - 完善 Cookie / token / fakeid 使用方式
  - 完成列表与详情抓取
- 通道失败分类：
  - 区分凭证失效
  - 区分风控
  - 区分临时网络失败

原因：

- 当前架构已经足够承载真实抓取器
- 现在继续打磨抓取器收益最大

## 6. 次级待办

完成上面两项后，再继续做下面这些。

### 6.1 反爬与代理策略深化

- 将代理选择从“能分服务类型”升级到“链路级策略”
- 增加随机延迟、限频、失败冷却
- 增加抓取账号连续失败惩罚

### 6.2 前端剩余页面全面切换

- 清理仍依赖旧 `/accounts` 语义的页面和 store
- 统一所有页面只使用 `collector` / `monitored` 两套接口

### 6.3 日志和监控增强

- 将日志页从“最近任务”扩展到“可筛选的抓取事件中心”
- 增加错误类型统计和账号健康概览

### 6.4 旧接口下线

- 在新页面全部完成切换后
- 逐步下线旧 `/accounts`、旧 `/qr`、旧服务层兼容包装

## 7. 当前建议的继续执行顺序

建议严格按下面顺序继续，不要跳着做：

1. 做旧数据迁移脚本
2. 跑迁移验证旧数据映射是否正确
3. 深化 `WeReadFetcher`
4. 深化 `MpAdminFetcher`
5. 加强代理和风控策略
6. 清理旧接口和旧语义

## 8. 一句话总结

当前项目已经完成了“目标态重构的骨架化改造”，现在最关键的不是继续堆页面，而是：

**先把旧数据迁移完成，再把真实抓取器做实。**
