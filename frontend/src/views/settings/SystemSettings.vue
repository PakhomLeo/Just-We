<template>
  <div class="system-settings">
    <div class="settings-grid">
      <section class="panel card-static">
        <h3>AI 分析配置</h3>
        <el-form label-position="top">
          <el-form-item label="API URL">
            <el-input v-model="settings.ai.api_url" />
          </el-form-item>
          <el-form-item label="API Key">
            <el-input v-model="settings.ai.api_key" show-password />
          </el-form-item>
          <el-form-item label="模型名称">
            <el-input v-model="settings.ai.model" />
          </el-form-item>
          <el-form-item label="Prompt 模板">
            <el-input v-model="settings.ai.prompt_template" type="textarea" :rows="8" />
          </el-form-item>
          <el-form-item label="启用 AI">
            <el-switch v-model="settings.ai.enabled" />
          </el-form-item>
        </el-form>
      </section>

      <section class="panel card-static">
        <h3>抓取策略</h3>
        <el-form label-position="top">
          <el-form-item label="Tier 阈值">
            <div class="inline-grid">
              <el-input-number v-model="settings.fetchPolicy.tier_thresholds.tier1" :min="0" :max="100" />
              <el-input-number v-model="settings.fetchPolicy.tier_thresholds.tier2" :min="0" :max="100" />
              <el-input-number v-model="settings.fetchPolicy.tier_thresholds.tier3" :min="0" :max="100" />
              <el-input-number v-model="settings.fetchPolicy.tier_thresholds.tier4" :min="0" :max="100" />
            </div>
          </el-form-item>
          <el-form-item label="Tier 轮询间隔（小时）">
            <div class="inline-grid">
              <el-input-number v-model="settings.fetchPolicy.check_intervals['1']" :min="1" />
              <el-input-number v-model="settings.fetchPolicy.check_intervals['2']" :min="1" />
              <el-input-number v-model="settings.fetchPolicy.check_intervals['3']" :min="1" />
              <el-input-number v-model="settings.fetchPolicy.check_intervals['4']" :min="1" />
              <el-input-number v-model="settings.fetchPolicy.check_intervals['5']" :min="1" />
            </div>
          </el-form-item>
          <el-form-item label="主通道映射">
            <div class="policy-list">
              <div v-for="tier in ['1', '2', '3', '4', '5']" :key="tier" class="policy-row">
                <span>Tier {{ tier }}</span>
                <el-select v-model="settings.fetchPolicy.primary_modes[tier]" style="width: 180px">
                  <el-option label="weread" value="weread" />
                  <el-option label="mp_admin" value="mp_admin" />
                </el-select>
              </div>
            </div>
          </el-form-item>
          <el-form-item label="重试次数">
            <el-input-number v-model="settings.fetchPolicy.retry_limit" :min="0" :max="10" />
          </el-form-item>
          <el-form-item label="重试退避（秒）">
            <el-input-number v-model="settings.fetchPolicy.retry_backoff_seconds" :min="1" :max="600" />
          </el-form-item>
          <el-form-item label="随机延迟范围（毫秒）">
            <div class="inline-grid inline-grid-two">
              <el-input-number v-model="settings.fetchPolicy.random_delay_min_ms" :min="0" />
              <el-input-number v-model="settings.fetchPolicy.random_delay_max_ms" :min="0" />
            </div>
          </el-form-item>
        </el-form>
      </section>

      <section class="panel card-static">
        <h3>邮件告警</h3>
        <el-form label-position="top">
          <el-form-item label="启用邮件通知">
            <el-switch v-model="settings.notificationEmail.enabled" />
          </el-form-item>
          <template v-if="settings.notificationEmail.enabled">
            <el-form-item label="SMTP Host">
              <el-input v-model="settings.notificationEmail.smtp_host" />
            </el-form-item>
            <el-form-item label="SMTP Port">
              <el-input-number v-model="settings.notificationEmail.smtp_port" :min="1" :max="65535" style="width: 100%" />
            </el-form-item>
            <el-form-item label="SMTP 用户名">
              <el-input v-model="settings.notificationEmail.smtp_username" />
            </el-form-item>
            <el-form-item label="SMTP 密码">
              <el-input v-model="settings.notificationEmail.smtp_password" show-password />
            </el-form-item>
            <el-form-item label="发件人邮箱">
              <el-input v-model="settings.notificationEmail.from_email" />
            </el-form-item>
            <el-form-item label="收件人邮箱">
              <el-input
                :model-value="settings.notificationEmail.to_emails.join(', ')"
                placeholder="ops@example.com, admin@example.com"
                @update:model-value="updateRecipients"
              />
            </el-form-item>
            <el-form-item label="启用 TLS">
              <el-switch v-model="settings.notificationEmail.use_tls" />
            </el-form-item>
          </template>
        </el-form>
      </section>

      <section class="panel card-static">
        <h3>开发默认管理员</h3>
        <el-alert
          title="系统启动时会自动确保默认管理员存在"
          type="info"
          :closable="false"
          show-icon
        />
        <el-descriptions :column="1" border class="admin-box">
          <el-descriptions-item label="邮箱">admin@admin.com</el-descriptions-item>
          <el-descriptions-item label="别名登录">admin</el-descriptions-item>
          <el-descriptions-item label="密码">admin123</el-descriptions-item>
        </el-descriptions>
      </section>
    </div>

    <div class="save-bar">
      <el-button @click="reloadSettings">重置</el-button>
      <el-button type="primary" :loading="saving" @click="handleSave">保存全部配置</el-button>
    </div>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getAIConfig,
  getFetchPolicy,
  getNotificationEmailConfig,
  updateAIConfig,
  updateFetchPolicy,
  updateNotificationEmailConfig
} from '@/api/system'

const saving = ref(false)
const settings = reactive({
  ai: {
    api_url: '',
    api_key: '',
    model: '',
    prompt_template: '',
    enabled: true
  },
  fetchPolicy: {
    tier_thresholds: { tier1: 80, tier2: 65, tier3: 50, tier4: 35 },
    check_intervals: { 1: 24, 2: 48, 3: 72, 4: 144, 5: 336 },
    primary_modes: { 1: 'weread', 2: 'weread', 3: 'mp_admin', 4: 'mp_admin', 5: 'mp_admin' },
    retry_limit: 2,
    retry_backoff_seconds: 30,
    random_delay_min_ms: 500,
    random_delay_max_ms: 2000
  },
  notificationEmail: {
    enabled: false,
    smtp_host: '',
    smtp_port: 587,
    smtp_username: '',
    smtp_password: '',
    from_email: '',
    to_emails: [],
    use_tls: true
  }
})

onMounted(reloadSettings)

async function reloadSettings() {
  try {
    const [aiRes, fetchPolicyRes, notificationEmailRes] = await Promise.all([
      getAIConfig(),
      getFetchPolicy(),
      getNotificationEmailConfig()
    ])
    Object.assign(settings.ai, aiRes.data)
    settings.fetchPolicy = {
      ...settings.fetchPolicy,
      ...fetchPolicyRes.data,
      tier_thresholds: { ...settings.fetchPolicy.tier_thresholds, ...fetchPolicyRes.data.tier_thresholds },
      check_intervals: { ...settings.fetchPolicy.check_intervals, ...fetchPolicyRes.data.check_intervals },
      primary_modes: { ...settings.fetchPolicy.primary_modes, ...fetchPolicyRes.data.primary_modes }
    }
    Object.assign(settings.notificationEmail, notificationEmailRes.data)
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.response?.data?.error || '系统设置加载失败')
  }
}

function updateRecipients(value) {
  settings.notificationEmail.to_emails = value
    .split(',')
    .map((item) => item.trim())
    .filter(Boolean)
}

async function handleSave() {
  saving.value = true
  try {
    await Promise.all([
      updateAIConfig(settings.ai),
      updateFetchPolicy(settings.fetchPolicy),
      updateNotificationEmailConfig(settings.notificationEmail)
    ])
    ElMessage.success('系统设置已保存')
  } finally {
    saving.value = false
  }
}
</script>

<style lang="scss" scoped>
.system-settings {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.settings-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.panel {
  padding: 24px;
}

.panel h3 {
  margin-top: 0;
}

.inline-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
  width: 100%;
}

.inline-grid-two {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.policy-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.policy-row {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.admin-box {
  margin-top: 16px;
}

  .save-bar {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }

@media (max-width: 960px) {
  .settings-grid,
  .inline-grid,
  .inline-grid-two {
    grid-template-columns: 1fr;
  }

  .policy-row,
  .save-bar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
