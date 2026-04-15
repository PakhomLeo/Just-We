<template>
  <div class="tier-pie-chart card-static">
    <h3 class="chart-title">Tier 分布</h3>
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts'

const props = defineProps({
  data: {
    type: Array,
    default: () => []
  }
})

const chartRef = ref(null)
let chart = null

const tierColors = {
  'S': '#FF3D00',
  'A': '#FF6B00',
  'B': '#22C55E',
  'C': '#3B82F6'
}

onMounted(() => {
  chart = echarts.init(chartRef.value)
  updateChart()
  window.addEventListener('resize', handleResize)
})

onUnmounted(() => {
  window.removeEventListener('resize', handleResize)
  chart?.dispose()
})

watch(() => props.data, updateChart, { deep: true })

function handleResize() {
  chart?.resize()
}

function updateChart() {
  if (!chart) return

  const pieData = props.data.map(item => ({
    name: item.tier,
    value: item.count,
    itemStyle: { color: tierColors[item.tier] || '#666' }
  }))

  const option = {
    tooltip: {
      trigger: 'item'
    },
    legend: {
      orient: 'vertical',
      right: 10,
      top: 'center'
    },
    series: [{
      type: 'pie',
      radius: ['40%', '70%'],
      center: ['40%', '50%'],
      avoidLabelOverlap: false,
      label: {
        show: false
      },
      emphasis: {
        label: {
          show: true,
          fontSize: 14,
          fontWeight: 'bold'
        }
      },
      data: pieData
    }]
  }

  chart.setOption(option)
}
</script>

<style lang="scss" scoped>
.tier-pie-chart {
  padding: 20px;
  height: 100%;
}

.chart-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.chart-container {
  height: 280px;
}
</style>
