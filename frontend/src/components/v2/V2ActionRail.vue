<template>
  <div class="v2-action-rail">
    <span>{{ label }}</span>
  </div>
</template>

<script setup>
defineProps({
  label: {
    type: String,
    required: true
  }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.v2-action-rail {
  margin-top: 24px;
  border-radius: 28px;
  background: $v2-card-soft;
  color: $v2-ink;
  padding: 18px 28px;
  font-size: 18px;
  font-weight: 900;
  line-height: 1.45;
  word-break: keep-all;
  box-shadow: inset 0 0 0 1px rgba($v2-line, 0.5);
}
</style>
