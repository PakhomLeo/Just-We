<template>
  <div class="app-layout">
    <AppSidebar />
    <div class="main-container" :class="{ 'sidebar-collapsed': appStore.sidebarCollapsed }">
      <AppHeader />
      <main class="content">
        <router-view />
      </main>
    </div>
  </div>
</template>

<script setup>
import { useAppStore } from '@/stores/app'
import AppSidebar from './AppSidebar.vue'
import AppHeader from './AppHeader.vue'

const appStore = useAppStore()
</script>

<style lang="scss" scoped>
.app-layout {
  display: flex;
  min-height: 100vh;
}

.main-container {
  flex: 1;
  margin-left: $sidebar-width;
  transition: margin-left $transition-normal;
  min-width: 0;

  &.sidebar-collapsed {
    margin-left: $sidebar-collapsed-width;
  }
}

.content {
  padding: 24px;
  background-color: $color-bg;
  min-height: calc(100vh - $header-height);
}

@media (max-width: 960px) {
  .main-container {
    margin-left: $sidebar-collapsed-width;
  }

  .content {
    padding: 16px;
  }
}

@media (max-width: 768px) {
  .content {
    padding: 12px;
  }
}
</style>
