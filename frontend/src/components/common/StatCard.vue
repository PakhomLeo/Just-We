<template>
  <div class="stat-card card-hover">
    <div class="stat-icon" :style="{ backgroundColor: iconBg }">
      <el-icon :size="28" :color="iconColor">
        <component :is="icon" />
      </el-icon>
    </div>
    <div class="stat-content">
      <p class="stat-label">{{ label }}</p>
      <p class="stat-value">{{ displayValue }}</p>
    </div>
  </div>
</template>

<script setup>
import { computed, ref, watch } from 'vue'

const props = defineProps({
  label: String,
  value: [Number, String],
  icon: [String, Object],
  iconColor: {
    type: String,
    default: '#FF6B00'
  },
  iconBg: {
    type: String,
    default: 'rgba(255, 107, 0, 0.1)'
  },
  duration: {
    type: Number,
    default: 1500
  }
})

const displayValue = ref(0)
const isStringValue = ref(false)

watch(() => props.value, (newVal) => {
  if (typeof newVal === 'string') {
    isStringValue.value = true
    displayValue.value = newVal
  } else {
    isStringValue.value = false
    if (newVal !== displayValue.value) {
      animateValue(newVal)
    }
  }
}, { immediate: true })

function animateValue(target) {
  const start = displayValue.value
  if (start === target) return

  const increment = (target - start) / (props.duration / 16)
  let current = start

  const animate = () => {
    current += increment
    if ((increment > 0 && current >= target) || (increment < 0 && current <= target)) {
      displayValue.value = target
      return
    }
    displayValue.value = Math.round(current)
    requestAnimationFrame(animate)
  }

  animate()
}
</script>

<style lang="scss" scoped>
.stat-card {
  display: flex;
  align-items: center;
  gap: 16px;
  padding: 24px;
  background: $color-card;
  border-radius: $radius-md;
}

.stat-icon {
  width: 56px;
  height: 56px;
  border-radius: $radius-sm;
  display: flex;
  align-items: center;
  justify-content: center;
}

.stat-content {
  flex: 1;
}

.stat-label {
  font-size: 14px;
  color: $color-text-secondary;
  margin-bottom: 4px;
}

.stat-value {
  font-size: 28px;
  font-weight: 700;
  color: $color-text;
}
</style>
