<template>
  <div class="v2-empty">
    <strong>{{ title }}</strong>
    <p>{{ description }}</p>
  </div>
</template>

<script setup>
defineProps({
  title: { type: String, default: '暂无数据' },
  description: { type: String, default: '请先创建数据或调整筛选条件。' }
})
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.v2-empty {
  border-radius: 24px;
  background: $v2-card-soft;
  padding: 34px;
  text-align: center;
  color: $v2-muted;

  strong {
    display: block;
    color: $v2-ink;
    font-size: 18px;
    font-weight: 950;
    margin-bottom: 6px;
  }

  p {
    margin: 0;
    font-weight: 700;
  }
}
</style>
