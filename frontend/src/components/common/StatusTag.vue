<template>
  <el-tag :type="tagType" :effect="effect" size="small">
    <slot>{{ text }}</slot>
  </el-tag>
</template>

<script setup>
import { computed } from 'vue'

const props = defineProps({
  status: {
    type: String,
    default: 'default'
  },
  tier: {
    type: String,
    default: null
  }
})

const effect = 'light'

const tagType = computed(() => {
  if (props.tier) {
    const tierMap = {
      'S': 'danger',
      'A': 'warning',
      'B': 'success',
      'C': 'info'
    }
    return tierMap[props.tier] || 'info'
  }

  const statusMap = {
    active: 'success',
    inactive: 'info',
    error: 'danger',
    pending: 'warning',
    monitoring: 'success',
    paused: 'info',
    risk_observed: 'warning',
    invalid: 'danger',
    normal: 'success',
    restricted: 'warning',
    expired: 'danger',
    failed: 'danger',
    running: 'warning',
    success: 'success'
  }
  return statusMap[props.status] || 'info'
})

const text = computed(() => props.tier || props.status)
</script>
