<template>
  <header class="app-header">
    <div class="header-left">
      <h1 class="page-title">{{ pageTitle }}</h1>
      <p class="page-subtitle">{{ pageSubtitle }}</p>
    </div>

    <div class="header-right">
      <el-button v-if="notificationsStore.unreadCount" text @click="notificationsStore.markAllAsRead()">
        全部已读
      </el-button>

      <el-badge :value="notificationsStore.unreadCount" :hidden="notificationsStore.unreadCount === 0" :max="99">
        <el-button circle @click="showNotifications = true">
          <el-icon :size="20"><Bell /></el-icon>
        </el-button>
      </el-badge>

      <el-dropdown @command="handleCommand">
        <span class="user-info">
          <el-avatar :size="32">{{ initials }}</el-avatar>
          <span class="username">{{ authStore.user?.email }}</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <el-drawer v-model="showNotifications" title="系统通知" size="420px" @open="handleDrawerOpen">
      <div v-if="notificationsStore.loading" class="empty-notifications">
        正在加载通知...
      </div>
      <div v-else-if="notificationsStore.notifications.length === 0" class="empty-notifications">
        暂无通知
      </div>
      <el-scrollbar v-else>
        <div
          v-for="notification in notificationsStore.notifications"
          :key="notification.id"
          class="notification-item"
          :class="{ unread: !notification.is_read }"
        >
          <div class="notification-main" @click="notificationsStore.markAsRead(notification.id)">
            <p class="notification-title">{{ notification.title }}</p>
            <p class="notification-content">{{ notification.content }}</p>
            <div class="notification-meta">
              <el-tag size="small" :type="getNotificationTagType(notification.notification_type)">
                {{ notification.notification_type }}
              </el-tag>
              <span class="notification-time">{{ formatTime(notification.created_at) }}</span>
            </div>
          </div>
          <el-button text @click="notificationsStore.removeNotification(notification.id)">删除</el-button>
        </div>
      </el-scrollbar>
    </el-drawer>
  </header>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { Bell } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()
const showNotifications = ref(false)

const titleMap = {
  Dashboard: ['仪表盘', '概览抓取账号、监测对象、告警与最新文章'],
  MpAccounts: ['公众号监测', '管理监测源、轮询层级与手动抓取'],
  CaptureAccounts: ['抓取账号', '绑定 WeRead / 公众号后台账号并监控健康状态'],
  Articles: ['文章列表', '按公众号、时间和相关度筛选采集结果'],
  ArticleDetail: ['文章详情', '查看正文、本地化图片与 AI 判定结果'],
  Proxies: ['代理管理', '维护各抓取链路使用的代理池'],
  WeightConfig: ['权重模拟', '查看当前权重参数并模拟分层结果'],
  Logs: ['作业与日志', '查看抓取作业、失败原因和操作审计'],
  SystemUsers: ['系统用户', '管理员创建和维护平台用户'],
  Settings: ['系统设置', '维护 AI、调度和邮件告警配置']
}

const pageTitle = computed(() => titleMap[route.name]?.[0] || '控制台')
const pageSubtitle = computed(() => titleMap[route.name]?.[1] || 'DynamicWePubMonitor')
const initials = computed(() => (authStore.user?.email || 'U').slice(0, 1).toUpperCase())

watch(
  () => authStore.isAuthenticated,
  (value) => {
    if (value) {
      notificationsStore.fetchNotifications()
    }
  },
  { immediate: true }
)

function handleDrawerOpen() {
  notificationsStore.fetchNotifications()
}

function handleCommand(command) {
  if (command === 'logout') {
    authStore.logout()
    router.push({ name: 'Login' })
  }
}

function getNotificationTagType(notificationType) {
  if (notificationType.includes('expired') || notificationType.includes('invalid')) {
    return 'danger'
  }
  if (notificationType.includes('restricted') || notificationType.includes('risk')) {
    return 'warning'
  }
  if (notificationType.includes('high_relevance')) {
    return 'success'
  }
  return 'info'
}

function formatTime(timestamp) {
  if (!timestamp) return '-'
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date
  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)} 分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)} 小时前`
  return date.toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
.app-header {
  height: $header-height;
  background: $color-card;
  box-shadow: 0 2px 10px rgba(0, 0, 0, 0.05);
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 24px;
}

.header-left {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: $color-text;
  margin: 0;
}

.page-subtitle {
  font-size: 13px;
  color: $color-text-secondary;
  margin: 0;
}

.header-right {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 16px;
  justify-content: flex-end;
}

.user-info {
  display: flex;
  align-items: center;
  gap: 8px;
  cursor: pointer;
}

.username {
  color: $color-text;
  font-weight: 500;
}

.empty-notifications {
  text-align: center;
  color: $color-text-secondary;
  padding: 40px 0;
}

.notification-item {
  padding: 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
  display: flex;
  justify-content: space-between;
  gap: 12px;

  &.unread {
    background: rgba($color-primary, 0.05);
  }
}

.notification-main {
  flex: 1;
  cursor: pointer;
}

.notification-title {
  font-size: 14px;
  font-weight: 600;
  margin: 0 0 6px;
}

.notification-content {
  margin: 0 0 8px;
  color: $color-text-secondary;
  word-break: break-word;
}

.notification-meta {
  display: flex;
  align-items: center;
  gap: 8px;
}

.notification-time {
  font-size: 12px;
  color: $color-text-secondary;
}

@media (max-width: 768px) {
  .app-header {
    height: auto;
    padding: 12px 16px;
    align-items: flex-start;
    flex-direction: column;
    gap: 12px;
  }

  .header-right {
    width: 100%;
    justify-content: space-between;
  }

  .notification-item {
    flex-direction: column;
  }

  .username {
    max-width: 140px;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }
}
</style>
