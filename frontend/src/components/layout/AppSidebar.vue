<template>
  <aside class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
    <div class="logo">
      <img src="@/assets/images/logo.svg" alt="Logo" class="logo-img">
      <div v-if="!appStore.sidebarCollapsed" class="logo-copy">
        <span class="logo-text">DynamicWePubMonitor</span>
        <span class="logo-subtext">公众号监测控制台</span>
      </div>
    </div>

    <el-menu
      :default-active="activeMenu"
      :collapse="appStore.sidebarCollapsed"
      router
      class="sidebar-menu"
    >
      <el-menu-item index="/dashboard">
        <el-icon><Odometer /></el-icon>
        <template #title>仪表盘</template>
      </el-menu-item>

      <el-menu-item index="/capture-accounts">
        <el-icon><User /></el-icon>
        <template #title>抓取账号</template>
      </el-menu-item>

      <el-menu-item index="/mp-accounts">
        <el-icon><Monitor /></el-icon>
        <template #title>公众号监测</template>
      </el-menu-item>

      <el-menu-item index="/articles">
        <el-icon><Document /></el-icon>
        <template #title>文章列表</template>
      </el-menu-item>

      <el-menu-item index="/proxies">
        <el-icon><Connection /></el-icon>
        <template #title>代理管理</template>
      </el-menu-item>

      <el-menu-item v-if="authStore.isAdmin" index="/logs">
        <el-icon><Tickets /></el-icon>
        <template #title>作业与日志</template>
      </el-menu-item>

      <el-menu-item v-if="authStore.isAdmin" index="/system-users">
        <el-icon><UserFilled /></el-icon>
        <template #title>用户管理</template>
      </el-menu-item>

      <el-menu-item v-if="authStore.isAdmin" index="/weight">
        <el-icon><Setting /></el-icon>
        <template #title>权重模拟</template>
      </el-menu-item>

      <el-menu-item v-if="authStore.isAdmin" index="/settings">
        <el-icon><Tools /></el-icon>
        <template #title>系统设置</template>
      </el-menu-item>
    </el-menu>

    <div class="sidebar-toggle" @click="appStore.toggleSidebar">
      <el-icon :size="20">
        <ArrowLeft v-if="!appStore.sidebarCollapsed" />
        <ArrowRight v-else />
      </el-icon>
    </div>
  </aside>
</template>

<script setup>
import { computed } from 'vue'
import { useRoute } from 'vue-router'
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import {
  Odometer, User, UserFilled, Document, Connection, Setting,
  Tickets, Tools, ArrowLeft, ArrowRight, Monitor
} from '@element-plus/icons-vue'

const appStore = useAppStore()
const authStore = useAuthStore()
const route = useRoute()

const activeMenu = computed(() => {
  if (route.path.startsWith('/articles/')) return '/articles'
  return route.path
})
</script>

<style lang="scss" scoped>
.sidebar {
  position: fixed;
  left: 0;
  top: 0;
  bottom: 0;
  width: $sidebar-width;
  background: $color-card;
  box-shadow: 2px 0 10px rgba(0, 0, 0, 0.05);
  display: flex;
  flex-direction: column;
  transition: width $transition-normal;
  z-index: 100;

  &.collapsed {
    width: $sidebar-collapsed-width;
  }
}

.logo {
  display: flex;
  align-items: center;
  padding: 20px 16px;
  gap: 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.logo-copy {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.logo-img {
  width: 32px;
  height: 32px;
  flex-shrink: 0;
}

.logo-text {
  font-size: 18px;
  font-weight: 600;
  color: $color-primary;
  white-space: nowrap;
}

.logo-subtext {
  font-size: 12px;
  color: $color-text-secondary;
  white-space: nowrap;
}

.sidebar-menu {
  flex: 1;
  border-right: none;

  &:not(.el-menu--collapse) {
    width: 100%;
  }
}

.sidebar-toggle {
  padding: 16px;
  display: flex;
  justify-content: center;
  cursor: pointer;
  border-top: 1px solid rgba(0, 0, 0, 0.05);
  color: $color-text-secondary;
  transition: color $transition-fast;

  &:hover {
    color: $color-primary;
  }
}
</style>
