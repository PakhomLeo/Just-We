<template>
  <div class="empty-state">
    <el-icon :size="64" color="#ccc">
      <component :is="icon || 'FolderOpened'" />
    </el-icon>
    <p class="empty-title">{{ title || message || '暂无数据' }}</p>
    <p v-if="description" class="empty-description">{{ description }}</p>
    <slot />
  </div>
</template>

<script setup>
import { FolderOpened } from '@element-plus/icons-vue'

defineProps({
  icon: String,
  message: String,
  title: String,
  description: String
})
</script>

<style lang="scss" scoped>
.empty-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  padding: 60px 20px;
  text-align: center;
  gap: 6px;
}

.empty-title {
  margin-top: 16px;
  font-size: 16px;
  color: $color-text-secondary;
}

.empty-description {
  margin-top: 8px;
  font-size: 14px;
  color: $color-text-secondary;
}
</style>
