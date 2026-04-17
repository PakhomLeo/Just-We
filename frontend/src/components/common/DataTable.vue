<template>
  <el-table
    v-bind="$attrs"
    :data="data"
    :loading="loading"
    stripe
    border
    class="data-table"
  >
    <slot />
    <template #empty>
      <EmptyState :message="emptyText" />
    </template>
  </el-table>
</template>

<script setup>
import { defineProps } from 'vue'
import EmptyState from './EmptyState.vue'

defineProps({
  data: {
    type: Array,
    default: () => []
  },
  loading: {
    type: Boolean,
    default: false
  },
  emptyText: {
    type: String,
    default: '暂无数据'
  }
})
</script>

<style scoped>
.data-table {
  width: 100%;
}

.data-table :deep(.el-table__header) {
  font-weight: 600;
}

.data-table :deep(.el-table__row) {
  transition: background-color 0.2s ease;
}

.data-table :deep(.el-table__row:hover > td) {
  background-color: #f8f4f0;
}
</style>
