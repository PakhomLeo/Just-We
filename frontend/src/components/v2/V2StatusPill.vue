<template>
  <span class="v2-status-pill" :class="tone">{{ label }}</span>
</template>

<script setup>
defineProps({
  label: { type: [String, Number], required: true },
  tone: {
    type: String,
    default: 'neutral',
    validator: value => ['neutral', 'success', 'warning', 'danger', 'purple', 'yellow'].includes(value)
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.v2-status-pill {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: $v2-radius-pill;
  padding: 7px 12px;
  font-size: 12px;
  line-height: 1;
  font-weight: 900;
  background: $v2-card-soft;
  color: $v2-ink;
  white-space: nowrap;
}

.success {
  background: rgba(#22c55e, 0.14);
  color: #166534;
}

.warning {
  background: $v2-warning-bg;
  color: #a34100;
}

.danger {
  background: rgba($v2-orange, 0.14);
  color: $v2-orange;
}

.purple {
  background: rgba($v2-purple, 0.15);
  color: $v2-purple;
}

.yellow {
  background: $v2-yellow;
  color: $v2-ink;
}
</style>
