<template>
  <div class="v2-metric-card" :class="{ warm }">
    <span>{{ label }}</span>
    <strong>{{ value }}</strong>
    <small v-if="hint">{{ hint }}</small>
  </div>
</template>

<script setup>
defineProps({
  label: { type: String, required: true },
  value: { type: [String, Number], default: '-' },
  hint: { type: String, default: '' },
  warm: { type: Boolean, default: false }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.v2-metric-card {
  min-height: 118px;
  border-radius: 28px;
  background: $v2-card-soft;
  padding: 22px 24px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  gap: 8px;
  color: $v2-ink;

  &.warm {
    background: $v2-warning-bg;
  }

  span {
    color: $v2-muted;
    font-weight: 800;
    font-size: 13px;
  }

  strong {
    color: $v2-purple;
    font-size: 34px;
    line-height: 1;
    font-weight: 950;
  }

  small {
    color: $v2-muted;
    font-weight: 700;
  }
}
</style>
