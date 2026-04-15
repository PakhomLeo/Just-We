<template>
  <header class="app-header">
    <div class="header-left">
      <h1 class="page-title">{{ pageTitle }}</h1>
    </div>

    <div class="header-right">
      <el-badge :value="notificationsStore.unreadCount" :hidden="notificationsStore.unreadCount === 0" :max="99">
        <el-button circle @click="showNotifications = true">
          <el-icon :size="20"><Bell /></el-icon>
        </el-button>
      </el-badge>

      <el-dropdown @command="handleCommand">
        <span class="user-info">
          <el-avatar :size="32">{{ authStore.user?.username?.[0]?.toUpperCase() }}</el-avatar>
          <span class="username">{{ authStore.user?.username }}</span>
        </span>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </div>

    <el-drawer v-model="showNotifications" title="通知" size="360px">
      <div v-if="notificationsStore.notifications.length === 0" class="empty-notifications">
        暂无通知
      </div>
      <el-scrollbar v-else>
        <div
          v-for="notification in notificationsStore.notifications"
          :key="notification.id"
          class="notification-item"
          :class="{ unread: !notification.read }"
          @click="notificationsStore.markAsRead(notification.id)"
        >
          <p class="notification-content">{{ notification.content }}</p>
          <span class="notification-time">{{ formatTime(notification.timestamp) }}</span>
        </div>
      </el-scrollbar>
    </el-drawer>
  </header>
</template>

<script setup>
import { ref, computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'
import { Bell } from '@element-plus/icons-vue'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()
const showNotifications = ref(false)

const pageTitle = computed(() => {
  const titles = {
    Dashboard: '仪表盘',
    Accounts: '账号管理',
    Articles: '文章列表',
    ArticleDetail: '文章详情',
    Proxies: '代理管理',
    WeightConfig: '权重配置',
    Logs: '日志监控',
    Users: '用户管理',
    Settings: '系统设置'
  }
  return titles[route.name] || route.name
})

function handleCommand(command) {
  if (command === 'logout') {
    authStore.logout()
    router.push({ name: 'Login' })
  }
}

function formatTime(timestamp) {
  const date = new Date(timestamp)
  const now = new Date()
  const diff = now - date

  if (diff < 60000) return '刚刚'
  if (diff < 3600000) return `${Math.floor(diff / 60000)}分钟前`
  if (diff < 86400000) return `${Math.floor(diff / 3600000)}小时前`
  return date.toLocaleDateString()
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

.page-title {
  font-size: 20px;
  font-weight: 600;
  color: $color-text;
}

.header-right {
  display: flex;
  align-items: center;
  gap: 16px;
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
  cursor: pointer;

  &.unread {
    background: rgba($color-primary, 0.05);
  }
}

.notification-content {
  margin-bottom: 4px;
}

.notification-time {
  font-size: 12px;
  color: $color-text-secondary;
}
</style>
