<template>
  <div class="v2-app">
    <nav class="v2-pill-nav">
      <button class="brand" @click="router.push('/dashboard')">Just-We</button>
      <div class="nav-links">
        <button
          v-for="item in visibleNavItems"
          :key="item.key"
          :class="[{ active: item.active(route) }, { optional: item.optional }]"
          @click="router.push(item.to)"
        >
          {{ item.label }}
        </button>
      </div>
      <el-dropdown class="more-nav" trigger="click" @command="path => router.push(path)">
        <button class="more-nav-button">更多</button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item
              v-for="item in visibleNavItems"
              :key="item.key"
              :command="item.to"
              :class="{ active: item.active(route) }"
            >
              {{ item.label }}
            </el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
      <button class="icon-action" @click="showNotifications = true">
        <span class="bell">🔔</span><span v-if="notificationsStore.unreadCount" class="badge">{{ notificationsStore.unreadCount }}</span>
      </button>
      <el-dropdown @command="handleCommand">
        <button class="user-chip">{{ displayUserName }}</button>
        <template #dropdown>
          <el-dropdown-menu>
            <el-dropdown-item disabled>{{ authStore.user?.role || 'viewer' }}</el-dropdown-item>
            <el-dropdown-item command="settings" v-if="authStore.isAdmin">系统设置</el-dropdown-item>
            <el-dropdown-item command="logout">退出登录</el-dropdown-item>
          </el-dropdown-menu>
        </template>
      </el-dropdown>
    </nav>

    <main class="v2-main">
      <router-view />
    </main>

    <el-drawer v-model="showNotifications" title="系统通知" size="430px" @open="notificationsStore.fetchNotifications({ page_size: 50 })">
      <div class="drawer-toolbar">
        <el-button size="small" @click="notificationsStore.fetchNotifications({ unread_only: true, page_size: 50 })">仅看未读</el-button>
        <el-button size="small" type="warning" @click="notificationsStore.markAllAsRead()">全部已读</el-button>
      </div>
      <div v-if="notificationsStore.loading" class="drawer-empty">正在加载通知...</div>
      <div v-else-if="!notificationsStore.notifications.length" class="drawer-empty">暂无通知</div>
      <div v-else class="notification-list">
        <article
          v-for="item in notificationsStore.notifications"
          :key="item.id"
          class="notification-card"
          :class="{ unread: !item.is_read }"
        >
          <div @click="openNotification(item)">
            <strong>{{ item.title }}</strong>
            <p>{{ item.content }}</p>
            <small>{{ item.notification_type }} · {{ formatDateTime(item.created_at) }}</small>
          </div>
          <div class="v2-button-row">
            <el-button size="small" @click="notificationsStore.markAsRead(item.id)">已读</el-button>
            <el-button size="small" type="danger" plain @click="notificationsStore.removeNotification(item.id)">删除</el-button>
          </div>
        </article>
      </div>
    </el-drawer>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { useNotificationsStore } from '@/stores/notifications'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const notificationsStore = useNotificationsStore()
const showNotifications = ref(false)

const navItems = [
  { key: 'dashboard', label: '总览', to: '/dashboard', active: r => r.path === '/dashboard' },
  { key: 'accounts', label: '账号', to: '/capture-accounts', active: r => r.path.startsWith('/capture-accounts') },
  { key: 'monitor', label: '公众号', to: '/mp-accounts', active: r => r.path.startsWith('/mp-accounts') },
  { key: 'articles', label: '文章', to: '/articles', active: r => r.path.startsWith('/articles') },
  { key: 'exports', label: '导出', to: '/exports', active: r => r.path.startsWith('/exports') },
  { key: 'proxies', label: '代理', to: '/proxies', active: r => r.path.startsWith('/proxies') },
  { key: 'logs', label: '日志', to: '/logs', adminOnly: true, optional: true, active: r => r.path.startsWith('/logs') },
  { key: 'users', label: '用户', to: '/system-users', adminOnly: true, optional: true, active: r => r.path.startsWith('/system-users') },
  { key: 'weight', label: '策略', to: '/weight', adminOnly: true, optional: true, active: r => r.path.startsWith('/weight') },
  { key: 'settings', label: '设置', to: '/settings', adminOnly: true, optional: true, active: r => r.path.startsWith('/settings') }
]

const visibleNavItems = computed(() => navItems.filter(item => !item.adminOnly || authStore.isAdmin))
const displayUserName = computed(() => {
  const email = authStore.user?.email || 'user'
  return email.includes('@') ? email.split('@')[0] : email
})

onMounted(() => {
  notificationsStore.fetchNotifications().catch(() => {})
})

function openNotification(item) {
  notificationsStore.markAsRead(item.id)
  const data = item.payload || item.metadata_json || {}
  const articleId = data.article_id || item.article_id
  const monitoredAccountId = data.monitored_account_id || item.monitored_account_id
  const collectorAccountId = data.collector_account_id || item.collector_account_id
  const jobId = data.job_id || item.job_id
  if (articleId) router.push(`/articles/${articleId}`)
  else if (monitoredAccountId) router.push({ path: '/articles', query: { monitored_account_id: monitoredAccountId } })
  else if (collectorAccountId) router.push('/capture-accounts')
  else if (jobId) router.push('/logs')
}

function handleCommand(command) {
  if (command === 'logout') {
    authStore.logout()
    router.push({ name: 'Login' })
  }
  if (command === 'settings') router.push('/settings')
}

function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.v2-app {
  padding: 22px 32px 42px;
}

.v2-pill-nav {
  position: sticky;
  top: 18px;
  z-index: 20;
  min-height: 76px;
  border-radius: 48px;
  background:
    linear-gradient(to bottom left, rgba(226, 238, 245, 0.96) -10%, rgba(157, 184, 203, 0.9) 118%),
    rgba(188, 211, 225, 0.86);
  color: $v2-ink;
  display: flex;
  align-items: center;
  gap: 14px;
  padding: 14px 18px 14px 34px;
  border: 1px solid rgba(#fff, 0.62);
  box-shadow: 0 18px 45px rgba(74, 103, 125, 0.18), inset 0 1px 0 rgba(#fff, 0.65);
  backdrop-filter: blur(18px) saturate(1.14);
}

button {
  font: inherit;
}

.brand,
.nav-links button,
.more-nav-button,
.icon-action,
.user-chip {
  border: 0;
  cursor: pointer;
  font-weight: 950;
  border-radius: 999px;
  transition: transform 0.16s ease, opacity 0.16s ease, background 0.16s ease, color 0.16s ease;

  &:active {
    transform: scale(0.97);
  }
}

.brand {
  background: transparent;
  color: $v2-ink;
  font-size: 20px;
  white-space: nowrap;
}

.nav-links {
  flex: 1;
  display: flex;
  justify-content: center;
  gap: 8px;
  min-width: 0;

  button {
    background: transparent;
    color: rgba($v2-ink, 0.76);
    padding: 10px 14px;
    font-size: 15px;
    white-space: nowrap;

    &.active {
      background: $v2-yellow;
      color: $v2-ink;
    }
  }
}

.more-nav {
  display: none;
}

.more-nav-button {
  background: rgba(#fff, 0.38);
  color: $v2-ink;
  padding: 10px 14px;
  white-space: nowrap;
}

.icon-action {
  position: relative;
  width: 42px;
  height: 42px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  background: rgba(#fff, 0.36);
  color: $v2-ink;
  padding: 0;

  .bell {
    font-size: 15px;
    line-height: 1;
  }

  .badge {
    position: absolute;
    right: -4px;
    top: -5px;
    min-width: 18px;
    height: 18px;
    border-radius: 999px;
    background: $v2-yellow;
    color: $v2-ink;
    display: grid;
    place-items: center;
    padding: 0 5px;
    font-size: 11px;
    line-height: 1;
  }
}

.user-chip {
  background: rgba(#fff, 0.42);
  color: $v2-ink;
  padding: 12px 18px;
  white-space: nowrap;
}

.v2-main {
  max-width: 1440px;
  margin: 24px auto 0;
}

.drawer-toolbar {
  display: flex;
  gap: 10px;
  margin-bottom: 16px;
}

.drawer-empty {
  color: $v2-muted;
  text-align: center;
  padding: 40px 0;
  font-weight: 800;
}

.notification-list {
  display: flex;
  flex-direction: column;
  gap: 14px;
}

.notification-card {
  border-radius: 24px;
  background: $v2-card-soft;
  padding: 18px;

  &.unread {
    background: $v2-warning-bg;
  }

  strong {
    display: block;
    color: $v2-ink;
    font-weight: 950;
    margin-bottom: 8px;
  }

  p {
    margin: 0 0 8px;
    color: $v2-muted;
    font-weight: 700;
  }

  small {
    color: $v2-purple;
    font-weight: 800;
  }
}

@media (max-width: 1180px) {
  .v2-pill-nav {
    gap: 10px;
    padding-left: 24px;
  }

  .nav-links {
    justify-content: flex-start;

    button {
      padding: 9px 11px;
      font-size: 14px;
    }
  }
}

@media (max-width: 980px) {
  .nav-links .optional {
    display: none;
  }

  .more-nav {
    display: inline-flex;
  }
}

@media (max-width: 760px) {
  .v2-app {
    padding: 12px;
  }

  .v2-pill-nav {
    flex-wrap: wrap;
    border-radius: 34px;
  }

  .brand {
    font-size: 16px;
  }

  .nav-links {
    order: 5;
    width: 100%;
    overflow-x: auto;
  }
}
</style>
