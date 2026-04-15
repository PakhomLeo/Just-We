<template>
  <div class="system-settings">
    <div class="settings-layout">
      <div class="settings-menu">
        <el-menu :default-active="activeSection" @select="handleSelect">
          <el-menu-item index="general">
            <el-icon><Setting /></el-icon>
            <span>通用配置</span>
          </el-menu-item>
          <el-menu-item index="ai">
            <el-icon><Cpu /></el-icon>
            <span>AI Prompt</span>
          </el-menu-item>
          <el-menu-item index="notifications">
            <el-icon><Bell /></el-icon>
            <span>通知渠道</span>
          </el-menu-item>
          <el-menu-item index="data">
            <el-icon><Delete /></el-icon>
            <span>数据清理</span>
          </el-menu-item>
          <el-menu-item index="security">
            <el-icon><Lock /></el-icon>
            <span>安全</span>
          </el-menu-item>
        </el-menu>
      </div>

      <div class="settings-content">
        <div v-if="activeSection === 'general'" class="section-content card-static">
          <h3>通用配置</h3>
          <el-form label-position="top">
            <el-form-item label="系统名称">
              <el-input v-model="settings.systemName" />
            </el-form-item>
            <el-form-item label="默认抓取间隔 (分钟)">
              <el-input-number v-model="settings.defaultCrawlInterval" :min="5" />
            </el-form-item>
            <el-form-item label="最大并发抓取数">
              <el-input-number v-model="settings.maxConcurrentCrawls" :min="1" :max="10" />
            </el-form-item>
            <el-form-item label="启用自动抓取">
              <el-switch v-model="settings.autoCrawlEnabled" />
            </el-form-item>
          </el-form>
        </div>

        <div v-if="activeSection === 'ai'" class="section-content card-static">
          <h3>AI Prompt 配置</h3>
          <el-form label-position="top">
            <el-form-item label="文章分析 Prompt">
              <el-input
                v-model="settings.aiPrompts.articleAnalysis"
                type="textarea"
                :rows="6"
              />
            </el-form-item>
            <el-form-item label="AI 模型">
              <el-select v-model="settings.aiModel">
                <el-option label="GPT-4" value="gpt-4" />
                <el-option label="GPT-3.5 Turbo" value="gpt-3.5-turbo" />
                <el-option label="Claude 3" value="claude-3" />
              </el-select>
            </el-form-item>
            <el-form-item label="AI 判断阈值">
              <el-slider v-model="settings.aiThreshold" :min="0" :max="1" :step="0.1" show-input />
            </el-form-item>
          </el-form>
        </div>

        <div v-if="activeSection === 'notifications'" class="section-content card-static">
          <h3>通知渠道</h3>
          <el-form label-position="top">
            <el-form-item label="邮件通知">
              <el-switch v-model="settings.notificationChannels.email" />
            </el-form-item>
            <el-form-item v-if="settings.notificationChannels.email" label="邮件 SMTP 配置">
              <el-input v-model="settings.smtpConfig" type="textarea" :rows="3" placeholder="smtp.example.com:587:username:password" />
            </el-form-item>
            <el-form-item label="Webhook 通知">
              <el-switch v-model="settings.notificationChannels.webhook" />
            </el-form-item>
            <el-form-item v-if="settings.notificationChannels.webhook" label="Webhook URL">
              <el-input v-model="settings.webhookUrl" placeholder="https://..." />
            </el-form-item>
          </el-form>
        </div>

        <div v-if="activeSection === 'data'" class="section-content card-static">
          <h3>数据清理</h3>
          <el-form label-position="top">
            <el-form-item label="日志保留天数">
              <el-input-number v-model="settings.logRetentionDays" :min="7" :max="365" />
            </el-form-item>
            <el-form-item label="文章缓存保留天数">
              <el-input-number v-model="settings.articleCacheDays" :min="30" :max="365" />
            </el-form-item>
            <el-form-item>
              <el-button type="danger" @click="handleClearCache">
                清理所有缓存
              </el-button>
              <el-button type="danger" plain @click="handleClearLogs">
                清理历史日志
              </el-button>
            </el-form-item>
          </el-form>
        </div>

        <div v-if="activeSection === 'security'" class="section-content card-static">
          <h3>安全设置</h3>
          <el-form label-position="top">
            <el-form-item label="JWT 过期时间 (小时)">
              <el-input-number v-model="settings.jwtExpireHours" :min="1" :max="168" />
            </el-form-item>
            <el-form-item label="登录失败锁定">
              <el-switch v-model="settings.loginLockEnabled" />
            </el-form-item>
            <el-form-item v-if="settings.loginLockEnabled" label="最大失败次数">
              <el-input-number v-model="settings.maxLoginAttempts" :min="3" :max="10" />
            </el-form-item>
            <el-form-item label="启用双因素认证">
              <el-switch v-model="settings.twoFactorEnabled" />
            </el-form-item>
          </el-form>
        </div>

        <div class="save-bar" v-if="hasChanges">
          <el-button @click="resetSettings">重置</el-button>
          <el-button type="primary" @click="handleSave">保存设置</el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, computed } from 'vue'
import { ElMessage } from 'element-plus'
import { Setting, Cpu, Bell, Delete, Lock } from '@element-plus/icons-vue'

const activeSection = ref('general')

const settings = reactive({
  systemName: 'DynamicWePubMonitor',
  defaultCrawlInterval: 30,
  maxConcurrentCrawls: 5,
  autoCrawlEnabled: true,
  aiPrompts: {
    articleAnalysis: '请分析以下文章，判断是否为AI生成。要求返回JSON格式：{"is_ai": true/false, "reason": "原因"}'
  },
  aiModel: 'gpt-4',
  aiThreshold: 0.5,
  notificationChannels: {
    email: false,
    webhook: false
  },
  smtpConfig: '',
  webhookUrl: '',
  logRetentionDays: 30,
  articleCacheDays: 90,
  jwtExpireHours: 24,
  loginLockEnabled: true,
  maxLoginAttempts: 5,
  twoFactorEnabled: false
})

const originalSettings = JSON.stringify(settings)
const hasChanges = computed(() => JSON.stringify(settings) !== originalSettings)

function handleSelect(index) {
  activeSection.value = index
}

function handleSave() {
  ElMessage.success('设置已保存')
}

function resetSettings() {
  Object.assign(settings, JSON.parse(originalSettings))
}

function handleClearCache() {
  ElMessage.success('缓存已清理')
}

function handleClearLogs() {
  ElMessage.success('历史日志已清理')
}
</script>

<style lang="scss" scoped>
.system-settings {
  .settings-layout {
    display: grid;
    grid-template-columns: 240px 1fr;
    gap: 24px;
  }

  .settings-menu {
    :deep(.el-menu) {
      border: none;
      background: transparent;

      .el-menu-item {
        border-radius: $radius-sm;
        margin-bottom: 4px;

        &.is-active {
          background: rgba($color-primary, 0.1);
          color: $color-primary;
        }
      }
    }
  }

  .settings-content {
    min-width: 0;
  }

  .section-content {
    padding: 24px;

    h3 {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 24px;
      padding-bottom: 16px;
      border-bottom: 1px solid rgba(0, 0, 0, 0.05);
    }
  }

  .save-bar {
    position: fixed;
    bottom: 0;
    left: $sidebar-width;
    right: 0;
    padding: 16px 24px;
    background: $color-card;
    box-shadow: 0 -2px 10px rgba(0, 0, 0, 0.05);
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    z-index: 10;
  }
}
</style>
