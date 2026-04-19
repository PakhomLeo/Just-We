<template>
  <V2Page
    title="系统设置"
    subtitle="AI、抓取、代理、限频、通知和默认管理员分组配置；标明立即生效、Redis 依赖和重启边界。"
    watermark="SETTINGS"
    action-rail="设置功能：保存 AI 配置 / 保存限频 / 保存通知 / 测试邮件 / 配置 Redis / 标记需重启项"
  >
    <template #header-actions>
      <div class="v2-page-actions">
        <el-button @click="reloadSettings">重置</el-button>
        <el-button type="warning" :loading="saving" @click="handleSave">保存全部配置</el-button>
      </div>
    </template>

    <div class="settings-grid">
      <V2Section title="AI 文字解析" subtitle="立即生效；Prompt 后端会强制 JSON 输出。">
        <el-form label-position="top">
          <el-form-item label="启用 AI"><el-switch v-model="settings.ai.enabled" /></el-form-item>
          <el-form-item label="目标文章类型"><el-input v-model="settings.ai.target_article_type" /></el-form-item>
          <el-form-item label="文字 API URL"><el-input v-model="settings.ai.text_api_url" /></el-form-item>
          <el-form-item label="文字 API Key"><el-input v-model="settings.ai.text_api_key" show-password /></el-form-item>
          <el-form-item label="文字模型"><el-input v-model="settings.ai.text_model" /></el-form-item>
          <el-form-item label="文字全文解析 Prompt"><el-input v-model="settings.ai.text_analysis_prompt" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="类型判断 Prompt"><el-input v-model="settings.ai.type_judgment_prompt" type="textarea" :rows="4" /></el-form-item>
        </el-form>
      </V2Section>

      <V2Section title="AI 图片解析" subtitle="多模态图片解析；无图片时跳过。">
        <el-form label-position="top">
          <el-form-item label="启用图片解析"><el-switch v-model="settings.ai.image_enabled" /></el-form-item>
          <el-form-item label="图片 API URL"><el-input v-model="settings.ai.image_api_url" /></el-form-item>
          <el-form-item label="图片 API Key"><el-input v-model="settings.ai.image_api_key" show-password /></el-form-item>
          <el-form-item label="图片模型"><el-input v-model="settings.ai.image_model" /></el-form-item>
          <el-form-item label="图片内容解析 Prompt"><el-input v-model="settings.ai.image_analysis_prompt" type="textarea" :rows="6" /></el-form-item>
          <el-form-item label="超时秒数"><el-input-number v-model="settings.ai.timeout_seconds" :min="5" :max="300" /></el-form-item>
        </el-form>
      </V2Section>

      <V2Section title="抓取策略" subtitle="影响新任务；历史回填按策略逐页推进。">
        <el-form label-position="top">
          <el-form-item label="Tier 阈值">
            <div class="compact-control-grid">
              <el-input-number v-model="settings.fetchPolicy.tier_thresholds.tier1" :min="0" :max="100" />
              <el-input-number v-model="settings.fetchPolicy.tier_thresholds.tier2" :min="0" :max="100" />
              <el-input-number v-model="settings.fetchPolicy.tier_thresholds.tier3" :min="0" :max="100" />
              <el-input-number v-model="settings.fetchPolicy.tier_thresholds.tier4" :min="0" :max="100" />
            </div>
          </el-form-item>
          <el-form-item label="Tier 抓取方式">
            <div class="policy-list compact-control-grid">
              <div v-for="tier in ['1','2','3','4','5']" :key="tier">
                <span>Tier {{ tier }}</span>
                <el-select v-model="settings.fetchPolicy.primary_modes[tier]"><el-option label="weread" value="weread" /><el-option label="mp_admin" value="mp_admin" /></el-select>
              </div>
            </div>
          </el-form-item>
          <el-form-item label="文章内容抓取间隔">
            <div class="compact-control-grid">
              <label class="compact-field"><span>动态间隔</span><el-switch v-model="settings.fetchPolicy.article_content_interval_policy.dynamic_enabled" /></label>
              <label class="compact-field"><span>最小秒数</span><el-input-number v-model="settings.fetchPolicy.article_content_interval_policy.min_seconds" :min="10" :max="30" /></label>
              <label class="compact-field"><span>最大秒数</span><el-input-number v-model="settings.fetchPolicy.article_content_interval_policy.max_seconds" :min="60" :max="300" /></label>
            </div>
          </el-form-item>
          <el-form-item label="每日自动抓取">
            <div class="compact-control-grid">
              <label class="compact-field"><span>每日次数</span><el-input-number v-model="settings.fetchPolicy.daily_account_fetch_policy.daily_runs" :min="1" /></label>
              <label class="compact-field"><span>避开时段</span><strong>{{ settings.fetchPolicy.daily_account_fetch_policy.quiet_start }} - {{ settings.fetchPolicy.daily_account_fetch_policy.quiet_end }}</strong></label>
              <label class="compact-field"><span>手动允许夜间</span><el-switch v-model="settings.fetchPolicy.daily_account_fetch_policy.allow_manual_in_quiet_window" /></label>
              <label class="compact-field"><span>积压允许夜间</span><el-switch v-model="settings.fetchPolicy.daily_account_fetch_policy.allow_backlog_in_quiet_window" /></label>
            </div>
            <div class="policy-note">自动规划会按当日账号数和每日次数计算间隔，默认避开 23:00 到次日 06:00；手动和积压任务可继续运行。</div>
          </el-form-item>
          <div class="compact-control-grid">
            <el-form-item label="重试次数"><el-input-number v-model="settings.fetchPolicy.retry_limit" :min="0" :max="10" /></el-form-item>
            <el-form-item label="历史回填最大页数"><el-input-number v-model="settings.fetchPolicy.history_backfill_policy.max_pages" :min="1" /></el-form-item>
          </div>
        </el-form>
      </V2Section>

      <V2Section title="代理与限频" subtitle="生产环境限频需要 Redis 保证多进程一致。">
        <div class="v2-risk-note">所有服务默认可直连；只有账号或服务手动绑定代理后才优先使用代理，失败后仍会直连兜底。</div>
        <el-form label-position="top" style="margin-top: 16px">
          <el-form-item label="兼容字段：禁止微信直连"><el-switch v-model="settings.proxyPolicy.disable_direct_wechat_fetch" disabled /></el-form-item>
          <div class="compact-control-grid">
            <el-form-item label="最低成功率"><el-input-number v-model="settings.proxyPolicy.min_success_rate" :min="0" :max="100" /></el-form-item>
            <el-form-item label="全局每分钟"><el-input-number v-model="settings.rateLimitPolicy.global_limit_per_minute" :min="1" /></el-form-item>
            <el-form-item label="单账号每分钟"><el-input-number v-model="settings.rateLimitPolicy.account_limit_per_minute" :min="1" /></el-form-item>
            <el-form-item label="详情最小间隔秒"><el-input-number v-model="settings.rateLimitPolicy.detail_min_interval_seconds" :min="0" :step="0.5" /></el-form-item>
            <el-form-item label="代理失败冷却秒"><el-input-number v-model="settings.rateLimitPolicy.proxy_failure_cooldown_seconds" :min="1" /></el-form-item>
          </div>
        </el-form>
      </V2Section>

      <V2Section title="通知策略" subtitle="凭证 24h / 6h / 过期 / 风控冷却提醒。">
        <el-form label-position="top">
          <el-form-item label="启用邮件"><el-switch v-model="settings.notificationEmail.enabled" /></el-form-item>
          <el-form-item label="SMTP Host"><el-input v-model="settings.notificationEmail.smtp_host" /></el-form-item>
          <el-form-item label="SMTP Port"><el-input-number v-model="settings.notificationEmail.smtp_port" :min="1" :max="65535" /></el-form-item>
          <el-form-item label="SMTP 用户名"><el-input v-model="settings.notificationEmail.smtp_username" /></el-form-item>
          <el-form-item label="SMTP 密码"><el-input v-model="settings.notificationEmail.smtp_password" show-password /></el-form-item>
          <el-form-item label="收件人邮箱"><el-input :model-value="settings.notificationEmail.to_emails.join(', ')" @update:model-value="updateRecipients" /></el-form-item>
          <el-form-item label="启用 Webhook"><el-switch v-model="settings.notificationPolicy.webhook_enabled" /></el-form-item>
          <el-form-item label="Webhook URL"><el-input v-model="settings.notificationPolicy.webhook_url" /></el-form-item>
        </el-form>
      </V2Section>

      <V2Section title="系统与默认管理员" warning>
        <div class="v2-risk-note">开发态可以展示默认管理员；生产态应弱化或隐藏。部分配置需要重启进程后完全生效。</div>
        <div class="admin-box">
          <strong>admin@admin.com</strong>
          <span>别名：admin · 初始密码：admin123</span>
        </div>
      </V2Section>
    </div>
  </V2Page>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import V2Page from '@/components/v2/V2Page.vue'
import V2Section from '@/components/v2/V2Section.vue'
import {
  getAIConfig,
  getFetchPolicy,
  getNotificationEmailConfig,
  getNotificationPolicy,
  getProxyPolicy,
  getRateLimitPolicy,
  updateAIConfig,
  updateFetchPolicy,
  updateNotificationEmailConfig,
  updateNotificationPolicy,
  updateProxyPolicy,
  updateRateLimitPolicy
} from '@/api/system'

const saving = ref(false)
const settings = reactive({
  ai: { enabled: true, target_article_type: '', text_api_url: '', text_api_key: '', text_model: '', image_api_url: '', image_api_key: '', image_model: '', image_enabled: true, text_analysis_prompt: '', image_analysis_prompt: '', type_judgment_prompt: '', timeout_seconds: 60 },
  fetchPolicy: {
    tier_thresholds: { tier1: 80, tier2: 65, tier3: 50, tier4: 35 },
    check_intervals: { 1: 24, 2: 48, 3: 72, 4: 144, 5: 336 },
    primary_modes: { 1: 'weread', 2: 'weread', 3: 'mp_admin', 4: 'mp_admin', 5: 'mp_admin' },
    retry_limit: 2,
    retry_backoff_seconds: 30,
    random_delay_min_ms: 500,
    random_delay_max_ms: 2000,
    rate_limit_policy: {},
    notification_policy: {},
    history_backfill_policy: { max_pages: 10 },
    article_content_interval_policy: { dynamic_enabled: true, min_seconds: 20, max_seconds: 180 },
    daily_account_fetch_policy: { daily_runs: 2, quiet_start: '23:00', quiet_end: '06:00', allow_manual_in_quiet_window: true, allow_backlog_in_quiet_window: true }
  },
  rateLimitPolicy: { global_limit_per_minute: 60, account_limit_per_minute: 20, proxy_limit_per_minute: 30, monitored_limit_per_minute: 20, detail_min_interval_seconds: 1, proxy_failure_cooldown_seconds: 120 },
  proxyPolicy: { disable_direct_wechat_fetch: false, min_success_rate: 50, detail_rotation_strategy: 'round_robin', list_sticky_ttl_seconds: 1800 },
  notificationEmail: { enabled: false, smtp_host: '', smtp_port: 587, smtp_username: '', smtp_password: '', from_email: '', to_emails: [], use_tls: true },
  notificationPolicy: { credential_check_interval_hours: 6, expiring_notice_hours: [24, 6], webhook_enabled: false, webhook_url: '' }
})

onMounted(() => {
  reloadSettings()
  window.addEventListener('v2-save-settings', handleSave)
})
onUnmounted(() => window.removeEventListener('v2-save-settings', handleSave))

async function reloadSettings() {
  const [aiRes, fetchPolicyRes, notificationEmailRes, rateLimitPolicyRes, notificationPolicyRes, proxyPolicyRes] = await Promise.all([
    getAIConfig(),
    getFetchPolicy(),
    getNotificationEmailConfig(),
    getRateLimitPolicy(),
    getNotificationPolicy(),
    getProxyPolicy()
  ])
  Object.assign(settings.ai, aiRes.data)
  settings.ai.text_api_url ||= settings.ai.api_url
  settings.ai.text_api_key ||= settings.ai.api_key
  settings.ai.text_model ||= settings.ai.model
  settings.ai.image_api_url ||= settings.ai.api_url
  settings.ai.image_api_key ||= settings.ai.api_key
  settings.ai.image_model ||= settings.ai.model
  settings.ai.text_analysis_prompt ||= settings.ai.prompt_template
  Object.assign(settings.fetchPolicy, fetchPolicyRes.data)
  settings.fetchPolicy.tier_thresholds = { tier1: 80, tier2: 65, tier3: 50, tier4: 35, ...(fetchPolicyRes.data.tier_thresholds || {}) }
  settings.fetchPolicy.primary_modes = { 1: 'weread', 2: 'weread', 3: 'mp_admin', 4: 'mp_admin', 5: 'mp_admin', ...(fetchPolicyRes.data.primary_modes || {}) }
  settings.fetchPolicy.history_backfill_policy = { max_pages: 10, ...(fetchPolicyRes.data.history_backfill_policy || {}) }
  settings.fetchPolicy.article_content_interval_policy = { dynamic_enabled: true, min_seconds: 20, max_seconds: 180, ...(fetchPolicyRes.data.article_content_interval_policy || {}) }
  settings.fetchPolicy.daily_account_fetch_policy = { daily_runs: 2, quiet_start: '23:00', quiet_end: '06:00', allow_manual_in_quiet_window: true, allow_backlog_in_quiet_window: true, ...(fetchPolicyRes.data.daily_account_fetch_policy || {}) }
  Object.assign(settings.notificationEmail, notificationEmailRes.data)
  Object.assign(settings.rateLimitPolicy, rateLimitPolicyRes.data)
  Object.assign(settings.notificationPolicy, notificationPolicyRes.data)
  Object.assign(settings.proxyPolicy, proxyPolicyRes.data)
}

function updateRecipients(value) {
  settings.notificationEmail.to_emails = value.split(',').map(item => item.trim()).filter(Boolean)
}

async function handleSave() {
  saving.value = true
  try {
    await Promise.all([
      updateAIConfig({ ...settings.ai, api_url: settings.ai.text_api_url, api_key: settings.ai.text_api_key, model: settings.ai.text_model, prompt_template: settings.ai.text_analysis_prompt }),
      updateFetchPolicy(settings.fetchPolicy),
      updateRateLimitPolicy(settings.rateLimitPolicy),
      updateProxyPolicy(settings.proxyPolicy),
      updateNotificationEmailConfig(settings.notificationEmail),
      updateNotificationPolicy(settings.notificationPolicy)
    ])
    ElMessage.success('系统设置已保存')
  } finally {
    saving.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.settings-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 22px;
}

.compact-control-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
  gap: 10px;
  align-items: center;
  justify-items: stretch;
  width: 100%;
  min-width: 0;

  :deep(.el-input-number),
  :deep(.el-select) {
    width: 100%;
    min-width: 0;
  }

  > :deep(.el-form-item) {
    min-width: 0;
    margin: 0;
    border-radius: 22px;
    background: $v2-card-soft;
    padding: 12px;
  }

  > :deep(.el-form-item .el-form-item__label) {
    justify-content: center;
    margin-bottom: 8px;
    color: $v2-muted;
    font-weight: 950;
    text-align: center;
    line-height: 1.3;
  }

  > :deep(.el-form-item .el-form-item__content) {
    min-width: 0;
    justify-content: center;
  }

  > :deep(.el-form-item .el-input-number) {
    max-width: 100%;
  }

  > :deep(.el-form-item .el-input-number .el-input__wrapper) {
    box-shadow: none;
    background: rgba(#fff, 0.54);
  }

  > :deep(.el-form-item .el-input-number__decrease),
  > :deep(.el-form-item .el-input-number__increase) {
    background: rgba(#fff, 0.62);
  }
}

.policy-list {
  > div {
    display: grid;
    grid-template-columns: 72px minmax(0, 1fr);
    gap: 10px;
    align-items: center;
  }
}

.compact-field {
  min-height: 54px;
  border-radius: 18px;
  background: $v2-card-soft;
  padding: 10px 12px;
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 10px;
  align-items: center;
  color: $v2-muted;
  font-weight: 900;
  min-width: 0;

  > span {
    flex: 1 1 92px;
  }

  :deep(.el-switch),
  :deep(.el-input-number),
  strong {
    flex: 1 1 150px;
    min-width: 0;
  }

  strong {
    color: $v2-ink;
    text-align: right;
  }
}

.policy-note {
  margin-top: 10px;
  color: $v2-muted;
  font-size: 13px;
  font-weight: 800;
  line-height: 1.6;
}

.admin-box {
  margin-top: 16px;
  border-radius: 22px;
  background: #fff;
  padding: 18px;
  display: grid;
  gap: 6px;

  strong {
    color: $v2-ink;
  }

  span {
    color: $v2-muted;
    font-weight: 800;
  }
}

@media (max-width: 1200px) {
  .settings-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 760px) {
  .settings-grid,
  .compact-control-grid {
    grid-template-columns: 1fr;
  }
}
</style>
