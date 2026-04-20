<template>
  <V2Page
    title="权重模拟与配置"
    subtitle="目标类型判断是“是/不是”，映射为 1.0 / 0.0 参与 Tier 计算。"
    watermark="WEIGHTS"
    action-rail="权重功能：保存权重 / 运行模拟 / 目标命中输入 / Tier 阈值 / 抓取间隔 / 恢复默认 / 查看得分拆解"
  >
    <div class="weight-grid">
      <V2Section title="当前权重配置" subtitle="直接承接 PUT /api/weight/config。">
        <el-form label-position="top">
          <div class="form-grid">
            <el-form-item label="频率权重"><el-input-number v-model="config.frequency_ratio" :min="0" :max="1" :step="0.05" /></el-form-item>
            <el-form-item label="时效权重"><el-input-number v-model="config.recency_ratio" :min="0" :max="1" :step="0.05" /></el-form-item>
            <el-form-item label="目标命中权重"><el-input-number v-model="config.relevance_ratio" :min="0" :max="1" :step="0.05" /></el-form-item>
            <el-form-item label="稳定性权重"><el-input-number v-model="config.stability_ratio" :min="0" :max="1" :step="0.05" /></el-form-item>
          </div>
          <el-form-item label="Tier 阈值（JSON）"><el-input v-model="tierThresholdsText" type="textarea" :rows="4" /></el-form-item>
          <el-form-item label="抓取间隔（JSON）"><el-input v-model="intervalsText" type="textarea" :rows="4" /></el-form-item>
        </el-form>
        <div class="v2-button-row">
          <el-button @click="loadConfig">恢复当前配置</el-button>
          <el-button type="warning" :loading="saving" @click="saveConfig">保存权重配置</el-button>
        </div>
      </V2Section>

      <V2Section title="模拟器" subtitle="目标命中“是”按 1.0，“不是”按 0.0。">
        <el-form label-position="top">
          <el-form-item label="最近更新时间"><el-date-picker v-model="simulation.last_update" type="datetime" value-format="YYYY-MM-DDTHH:mm:ss" style="width: 100%" /></el-form-item>
          <div class="form-grid">
            <el-form-item label="本轮新文章"><el-input-number v-model="simulation.new_articles" :min="0" /></el-form-item>
            <el-form-item label="目标类型命中"><el-select v-model="simulation.target_match"><el-option label="是" value="是" /><el-option label="不是" value="不是" /></el-select></el-form-item>
          </div>
          <el-form-item label="近 7 天更新数（逗号分隔）"><el-input v-model="updateSeries" /></el-form-item>
          <el-form-item label="近 7 天 AI 命中（是/不是逗号分隔）"><el-input v-model="aiSeries" /></el-form-item>
        </el-form>
        <el-button type="primary" :loading="simulating" @click="runSimulation">运行模拟</el-button>
        <div v-if="simulationResult" class="result-box">
          <strong>Tier {{ simulationResult.new_tier }} · 得分 {{ Math.round(simulationResult.new_score || 0) }}</strong>
          <pre class="v2-json">{{ jsonText(simulationResult) }}</pre>
        </div>
      </V2Section>
    </div>
  </V2Page>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage } from 'element-plus'
import V2Page from '@/components/v2/V2Page.vue'
import V2Section from '@/components/v2/V2Section.vue'
import { getWeightConfig, testWeightFormula, updateWeightConfig } from '@/api/weight'
import { jsonText } from './helpers'

const saving = ref(false)
const simulating = ref(false)
const simulationResult = ref(null)
const tierThresholdsText = ref('{}')
const intervalsText = ref('{}')
const updateSeries = ref('3,1,0,2,1,4,1')
const aiSeries = ref('是,不是,是,是,不是,是,是')
const config = reactive({ frequency_ratio: 0.3, recency_ratio: 0.25, relevance_ratio: 0.35, stability_ratio: 0.1, tier_thresholds: [], check_intervals: {}, high_relevance_threshold: 0.8, ai_consecutive_low_threshold: 3 })
const simulation = reactive({ last_update: new Date().toISOString().slice(0, 19), new_articles: 3, target_match: '是' })

onMounted(() => {
  loadConfig()
  window.addEventListener('v2-save-weight', saveConfig)
})
onUnmounted(() => window.removeEventListener('v2-save-weight', saveConfig))

async function loadConfig() {
  const response = await getWeightConfig()
  Object.assign(config, response.data)
  tierThresholdsText.value = JSON.stringify(config.tier_thresholds || {}, null, 2)
  intervalsText.value = JSON.stringify(config.check_intervals || {}, null, 2)
}

async function saveConfig() {
  saving.value = true
  try {
    const thresholds = JSON.parse(tierThresholdsText.value || '[]')
    const intervals = JSON.parse(intervalsText.value || '{}')
    await updateWeightConfig({
      frequency_ratio: config.frequency_ratio,
      recency_ratio: config.recency_ratio,
      relevance_ratio: config.relevance_ratio,
      stability_ratio: config.stability_ratio,
      tier_threshold_tier1: thresholds[0],
      tier_threshold_tier2: thresholds[1],
      tier_threshold_tier3: thresholds[2],
      tier_threshold_tier4: thresholds[3],
      check_interval_tier1: intervals['1'],
      check_interval_tier2: intervals['2'],
      check_interval_tier3: intervals['3'],
      check_interval_tier4: intervals['4'],
      check_interval_tier5: intervals['5'],
      high_relevance_threshold: config.high_relevance_threshold,
      ai_consecutive_low_threshold: config.ai_consecutive_low_threshold
    })
    ElMessage.success('权重配置已保存')
    await loadConfig()
  } finally {
    saving.value = false
  }
}

async function runSimulation() {
  simulating.value = true
  try {
    const payload = {
      last_updated: simulation.last_update,
      new_article_count: simulation.new_articles,
      ai_result: { target_match: simulation.target_match, ratio: simulation.target_match === '是' ? 1 : 0 },
      update_history: Object.fromEntries(updateSeries.value.split(',').map((count, index) => [`day_${index + 1}`, Number(count)])),
      ai_relevance_history: Object.fromEntries(aiSeries.value.split(',').map((item, index) => [`day_${index + 1}`, { match: item.trim(), ratio: item.trim() === '是' ? 1 : 0 }]))
    }
    const response = await testWeightFormula(payload)
    simulationResult.value = response.data
  } finally {
    simulating.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.weight-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(0, 1fr);
  gap: 24px;
  align-items: stretch;

  :deep(.v2-section) {
    height: 100%;
  }
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.result-box {
  margin-top: 18px;
  border-radius: 26px;
  background: $v2-purple;
  color: #fff;
  padding: 20px;
}

@media (max-width: 1000px) {
  .weight-grid,
  .form-grid {
    grid-template-columns: 1fr;
  }
}
</style>
