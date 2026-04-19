<template>
  <div class="v2-page">
    <div class="v2-watermark">{{ watermark }}</div>
    <section class="v2-stage">
      <header class="v2-page-header">
        <div>
          <h1>{{ title }}</h1>
          <p>{{ subtitle }}</p>
        </div>
        <slot name="header-actions" />
      </header>
      <slot />
    </section>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, required: true },
  subtitle: { type: String, default: '' },
  watermark: { type: String, default: 'MONITOR' },
  actionRail: { type: String, default: '' }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.v2-page {
  position: relative;
  min-height: calc(100vh - 140px);
}

.v2-watermark {
  position: absolute;
  top: 14px;
  left: 24px;
  pointer-events: none;
  color: rgba($v2-ink, 0.05);
  font-size: clamp(62px, 8vw, 116px);
  font-weight: 950;
  line-height: 1;
  letter-spacing: -0.06em;
  z-index: 0;
}

.v2-stage {
  position: relative;
  z-index: 1;
  min-height: calc(100vh - 164px);
  border-radius: 34px;
  background: linear-gradient(to bottom left, rgba($v2-panel, 0.98) -6%, rgba(#edf5fa, 0.96) 54%, rgba(#dfeaf3, 0.94) 120%);
  padding: 40px;
  box-shadow: $v2-shadow-soft;
  overflow: hidden;

  &::before {
    content: '';
    position: absolute;
    width: 620px;
    height: 620px;
    right: -230px;
    top: -260px;
    border-radius: 50%;
    background: radial-gradient(circle, rgba($v2-purple, 0.22), transparent 72%);
    filter: blur(18px);
    pointer-events: none;
  }

  :deep(.v2-grid + .v2-section),
  :deep(.v2-section + .v2-grid),
  :deep(.v2-section + .v2-section),
  :deep(.v2-grid + .v2-grid) {
    margin-top: 28px;
  }
}

.v2-page-header {
  position: relative;
  z-index: 1;
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
  gap: 24px;
  margin-bottom: 28px;

  h1 {
    margin: 0;
    color: $v2-ink;
    font-size: clamp(30px, 4vw, 44px);
    line-height: 1.06;
    font-weight: 950;
    letter-spacing: -0.05em;
  }

  p {
    margin: 10px 0 0;
    color: $v2-muted;
    font-weight: 700;
  }
}

@media (max-width: 900px) {
  .v2-stage {
    padding: 28px;
    border-radius: 28px;
  }

  .v2-page-header {
    flex-direction: column;
  }
}
</style>
