<template>
  <aside class="sidebar" :class="{ collapsed: appStore.sidebarCollapsed }">
    <div class="logo">
      <img src="@/assets/images/logo.svg" alt="Logo" class="logo-img">
      <span v-if="!appStore.sidebarCollapsed" class="logo-text">WePubMonitor</span>
    </div>

    <el-menu
      :default-active="$route.name"
      :collapse="appStore.sidebarCollapsed"
      router
      class="sidebar-menu"
    >
      <el-menu-item index="Dashboard">
        <el-icon><Odometer /></el-icon>
        <template #title>Dashboard</template>
      </el-menu-item>

      <el-menu-item index="Accounts">
        <el-icon><User /></el-icon>
        <template #title>账号管理</template>
      </el-menu-item>

      <el-menu-item index="Articles">
        <el-icon><Document /></el-icon>
        <template #title>文章列表</template>
      </el-menu-item>

      <el-menu-item index="Proxies">
        <el-icon><Connection /></el-icon>
        <template #title>代理管理</template>
      </el-menu-item>

      <el-menu-item v-if="authStore.isAdmin" index="WeightConfig">
        <el-icon><Setting /></el-icon>
        <template #title>权重配置</template>
      </el-menu-item>

      <el-menu-item v-if="authStore.isAdmin" index="Logs">
        <el-icon><Tickets /></el-icon>
        <template #title>日志监控</template>
      </el-menu-item>

      <el-menu-item v-if="authStore.isAdmin" index="Users">
        <el-icon><UserFilled /></el-icon>
        <template #title>用户管理</template>
      </el-menu-item>

      <el-menu-item v-if="authStore.isAdmin" index="Settings">
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
import { useAppStore } from '@/stores/app'
import { useAuthStore } from '@/stores/auth'
import {
  Odometer, User, Document, Connection, Setting,
  Tickets, UserFilled, Tools, ArrowLeft, ArrowRight
} from '@element-plus/icons-vue'

const appStore = useAppStore()
const authStore = useAuthStore()
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
