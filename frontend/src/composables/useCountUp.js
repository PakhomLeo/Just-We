import { ref, watch, computed } from 'vue'

/**
 * 数字动画 composable
 * 用于实现数字从起点到终点的动画效果
 *
 * @param {Object} options 配置选项
 * @param {number} options.startValue 起始值，默认 0
 * @param {number} options.endValue 目标值
 * @param {number} options.duration 动画时长(ms)，默认 1500
 * @param {number} options.decimalPlaces 小数位数，默认 0
 * @param {string} options.easing 缓动函数，默认 'easeOutCubic'
 */
export function useCountUp(options = {}) {
  const {
    startValue = 0,
    endValue = 0,
    duration = 1500,
    decimalPlaces = 0,
    easing = 'easeOutCubic'
  } = options

  const currentValue = ref(startValue)
  const isAnimating = ref(false)

  // 缓动函数
  const easingFunctions = {
    linear: t => t,
    easeOutCubic: t => 1 - Math.pow(1 - t, 3),
    easeOutQuart: t => 1 - Math.pow(1 - t, 4),
    easeOutExpo: t => t === 1 ? 1 : 1 - Math.pow(2, -10 * t)
  }

  const ease = easingFunctions[easing] || easingFunctions.easeOutCubic

  /**
   * 执行动画
   * @param {number} target 目标值
   * @param {number} start 起始值
   * @param {number} ms 持续时间
   */
  function animate(target, start, ms) {
    if (ms <= 0) {
      currentValue.value = target
      isAnimating.value = false
      return
    }

    isAnimating.value = true
    const startTime = performance.now()

    function update(currentTime) {
      const elapsed = currentTime - startTime
      const progress = Math.min(elapsed / ms, 1)
      const easedProgress = ease(progress)

      currentValue.value = start + (target - start) * easedProgress

      if (progress < 1) {
        requestAnimationFrame(update)
      } else {
        currentValue.value = target
        isAnimating.value = false
      }
    }

    requestAnimationFrame(update)
  }

  /**
   * 设置新值并触发动画
   * @param {number} newValue 新目标值
   * @param {number} customDuration 自定义动画时长
   */
  function setValue(newValue, customDuration) {
    const from = currentValue.value
    const to = typeof newValue === 'number' ? newValue : parseFloat(newValue) || 0
    animate(to, from, customDuration || duration)
  }

  /**
   * 重置到指定值（无动画）
   * @param {number} value 要重置的值
   */
  function reset(value = startValue) {
    currentValue.value = value
    isAnimating.value = false
  }

  // 监听 endValue 变化
  watch(() => endValue, (newVal) => {
    if (newVal !== currentValue.value) {
      setValue(newVal)
    }
  })

  /**
   * 格式化数字显示
   * @param {number} value 要格式化的值
   * @returns {string} 格式化后的字符串
   */
  function formatValue(value) {
    if (decimalPlaces > 0) {
      return value.toFixed(decimalPlaces)
    }
    return Math.round(value).toString()
  }

  return {
    currentValue,
    isAnimating,
    setValue,
    reset,
    formatValue
  }
}

/**
 * 带单位的数字动画
 * @param {Object} options 配置选项
 */
export function useCountUpWithUnit(options = {}) {
  const { unit = '', prefix = false, ...rest } = options
  const { currentValue, isAnimating, setValue, reset, formatValue } = useCountUp(rest)

  const displayValue = computed(() => {
    const formatted = formatValue(currentValue.value)
    return prefix ? `${unit}${formatted}` : `${formatted}${unit}`
  })

  return {
    currentValue,
    displayValue,
    isAnimating,
    setValue,
    reset
  }
}
