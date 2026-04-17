<template>
  <div class="weight-config">
    <div class="page-header">
      <div>
        <h2>权重模拟</h2>
        <p>这里展示当前后端权重配置，并提供模拟工具；真实抓取策略持久化配置请在系统设置中维护。</p>
      </div>
    </div>

    <div class="content-grid">
      <section class="panel card-static">
        <h3>当前配置</h3>
        <el-descriptions :column="1" border>
          <el-descriptions-item label="频率权重">{{ config.frequency_ratio }}</el-descriptions-item>
          <el-descriptions-item label="时效权重">{{ config.recency_ratio }}</el-descriptions-item>
          <el-descriptions-item label="相关度权重">{{ config.relevance_ratio }}</el-descriptions-item>
          <el-descriptions-item label="稳定性权重">{{ config.stability_ratio }}</el-descriptions-item>
          <el-descriptions-item label="Tier 阈值">{{ config.tier_thresholds.join(' / ') }}</el-descriptions-item>
          <el-descriptions-item label="抓取间隔">
            {{ Object.entries(config.check_intervals).map(([tier, hours]) => `Tier ${tier}: ${hours}h`).join('，') }}
          </el-descriptions-item>
          <el-descriptions-item label="高相关阈值">{{ config.high_relevance_threshold }}</el-descriptions-item>
          <el-descriptions-item label="连续低相关告警阈值">{{ config.ai_consecutive_low_threshold }}</el-descriptions-item>
        </el-descriptions>
      </section>

      <section class="panel card-static">
        <h3>模拟输入</h3>
        <el-form :model="simulationForm" label-position="top">
          <el-form-item label="最近一次发布时间">
            <el-date-picker v-model="simulationForm.last_updated" type="datetime" style="width: 100%" />
          </el-form-item>
          <el-form-item label="本轮新文章数">
            <el-input-number v-model="simulationForm.new_article_count" :min="0" />
          </el-form-item>
          <el-form-item label="当前 AI 相关度">
            <el-slider v-model="simulationForm.current_ratio" :min="0" :max="100" />
          </el-form-item>
          <el-form-item label="近 7 天更新次数（逗号分隔）">
            <el-input v-model="simulationForm.updateSeries" placeholder="3,1,0,2,1,4,1" />
          </el-form-item>
          <el-form-item label="近 7 次 AI 相关度（逗号分隔）">
            <el-input v-model="simulationForm.ratioSeries" placeholder="0.3,0.5,0.8,0.9" />
          </el-form-item>
          <el-button type="primary" :loading="simulating" @click="runSimulation">运行模拟</el-button>
        </el-form>
      </section>
    </div>

    <section v-if="simulationResult" class="panel card-static">
      <h3>模拟结果</h3>
      <div class="result-grid">
        <div class="result-item">
          <span>新得分</span>
          <strong>{{ simulationResult.new_score.toFixed(2) }}</strong>
        </div>
        <div class="result-item">
          <span>新 Tier</span>
          <strong>Tier {{ simulationResult.new_tier }}</strong>
        </div>
        <div class="result-item">
          <span>建议间隔</span>
          <strong>{{ simulationResult.next_interval_hours }} 小时</strong>
        </div>
      </div>
      <pre class="breakdown-viewer">{{ JSON.stringify(simulationResult.score_breakdown, null, 2) }}</pre>
    </section>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { getWeightConfig, testWeightFormula } from '@/api/weight'

const config = reactive({
  frequency_ratio: 0,
  recency_ratio: 0,
  relevance_ratio: 0,
  stability_ratio: 0,
  tier_thresholds: [],
  check_intervals: {},
  high_relevance_threshold: 0,
  ai_consecutive_low_threshold: 0
})

const simulationForm = reactive({
  last_updated: new Date(),
  new_article_count: 1,
  current_ratio: 60,
  updateSeries: '1,0,2,0,1,3,1',
  ratioSeries: '0.4,0.6,0.7,0.5,0.8,0.6,0.9'
})

const simulating = ref(false)
const simulationResult = ref(null)

onMounted(loadConfig)

async function loadConfig() {
  const response = await getWeightConfig()
  Object.assign(config, response.data)
}

async function runSimulation() {
  simulating.value = true
  try {
    const updateHistory = buildUpdateHistory(simulationForm.updateSeries)
    const aiHistory = buildAiHistory(simulationForm.ratioSeries)
    const response = await testWeightFormula({
      update_history: updateHistory,
      ai_relevance_history: aiHistory,
      last_updated: simulationForm.last_updated,
      new_article_count: simulationForm.new_article_count,
      ai_result: {
        ratio: simulationForm.current_ratio / 100,
        reason: 'frontend simulation'
      }
    })
    simulationResult.value = response.data
  } catch (error) {
    ElMessage.error('模拟失败，请检查输入格式')
  } finally {
    simulating.value = false
  }
}

function buildUpdateHistory(series) {
  return series.split(',').reduce((acc, value, index) => {
    const date = new Date()
    date.setDate(date.getDate() - index)
    acc[date.toISOString()] = Number(value.trim() || 0)
    return acc
  }, {})
}

function buildAiHistory(series) {
  return series.split(',').reduce((acc, value, index) => {
    const date = new Date()
    date.setDate(date.getDate() - index)
    acc[date.toISOString()] = { ratio: Number(value.trim() || 0), reason: 'history sample' }
    return acc
  }, {})
}
</script>

<style lang="scss" scoped>
.weight-config {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header h2 {
  margin: 0 0 6px;
}

.page-header p {
  margin: 0;
  color: $color-text-secondary;
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 24px;
}

.panel {
  padding: 24px;
}

.panel h3 {
  margin-top: 0;
}

.result-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 16px;
  margin-bottom: 20px;
}

.result-item {
  padding: 16px;
  border-radius: 12px;
  background: rgba($color-primary, 0.06);
  display: flex;
  flex-direction: column;
  gap: 6px;

  strong {
    font-size: 24px;
  }
}

.breakdown-viewer {
  background: $color-bg;
  border-radius: 12px;
  padding: 16px;
  margin: 0;
  overflow: auto;
}

@media (max-width: 900px) {
  .content-grid,
  .result-grid {
    grid-template-columns: 1fr;
  }
}
</style>
