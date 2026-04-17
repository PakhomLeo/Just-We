<template>
  <div class="trend-chart card-static">
    <h3 class="chart-title">抓取趋势</h3>
    <div ref="chartRef" class="chart-container"></div>
  </div>
</template>

<script setup>
import { ref, onMounted, onUnmounted, watch } from 'vue'
import * as echarts from 'echarts/core'
import { LineChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, GraphicComponent } from 'echarts/components'
import { CanvasRenderer } from 'echarts/renderers'

// Register only required components for tree-shaking to work
echarts.use([LineChart, GridComponent, TooltipComponent, GraphicComponent, CanvasRenderer])

const props = defineProps({
  data: {
    type: Object,
    default: () => ({
      dates: [],
      values: []
    })
  }
})

const chartRef = ref(null)
let chart = null

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

  const option = {
    tooltip: {
      trigger: 'axis'
    },
    xAxis: {
      type: 'category',
      data: props.data.dates,
      boundaryGap: false
    },
    yAxis: {
      type: 'value'
    },
    series: [{
      data: props.data.values,
      type: 'line',
      smooth: true,
      areaStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: 'rgba(255, 107, 0, 0.3)' },
          { offset: 1, color: 'rgba(255, 107, 0, 0)' }
        ])
      },
      lineStyle: {
        color: '#FF6B00'
      },
      itemStyle: {
        color: '#FF6B00'
      }
    }]
  }

  chart.setOption(option)
}
</script>

<style lang="scss" scoped>
.trend-chart {
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
