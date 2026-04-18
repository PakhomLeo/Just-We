<template>
  <section class="v2-section" :class="{ purple, warning }">
    <div v-if="title || $slots.actions" class="v2-section-header">
      <div>
        <h2 v-if="title">{{ title }}</h2>
        <p v-if="subtitle">{{ subtitle }}</p>
      </div>
      <div v-if="$slots.actions" class="v2-section-actions">
        <slot name="actions" />
      </div>
    </div>
    <slot />
  </section>
</template>

<script setup>
defineProps({
  title: { type: String, default: '' },
  subtitle: { type: String, default: '' },
  purple: { type: Boolean, default: false },
  warning: { type: Boolean, default: false }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.v2-section {
  position: relative;
  border-radius: 30px;
  background: #fff;
  padding: 26px;
  box-shadow: inset 0 0 0 1px rgba($v2-line, 0.45);
  min-width: 0;

  &.purple {
    background: $v2-purple;
    color: #fff;

    p {
      color: rgba(#fff, 0.72);
    }
  }

  &.warning {
    background: $v2-warning-bg;
  }
}

.v2-section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;

  h2 {
    margin: 0;
    color: inherit;
    font-size: 22px;
    font-weight: 950;
    letter-spacing: -0.03em;
  }

  p {
    margin: 6px 0 0;
    color: $v2-muted;
    font-size: 13px;
    font-weight: 700;
  }
}

.v2-section-actions {
  display: flex;
  flex-wrap: wrap;
  justify-content: flex-end;
  gap: 10px;
}
</style>
