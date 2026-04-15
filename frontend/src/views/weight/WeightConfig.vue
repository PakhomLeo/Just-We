<template>
  <div class="weight-config">
    <div class="page-header">
      <h2>权重配置</h2>
      <el-alert
        v-if="!isAdmin"
        title="仅管理员可修改权重配置"
        type="warning"
        :closable="false"
        show-icon
      />
    </div>

    <div class="config-layout">
      <div class="config-left card-static">
        <h3>Score 计算公式</h3>
        <div class="formula-display">
          <pre class="formula-text">
Score = base_score
      + tier_interval_bonus
      + engagement_score
      + recency_bonus
      - penalty deductions
          </pre>
        </div>

        <div class="factor-list">
          <h4>各因子说明</h4>
          <div class="factor-item">
            <span class="factor-name">tier_interval_bonus</span>
            <span class="factor-desc">根据 Tier 等级和抓取间隔计算</span>
          </div>
          <div class="factor-item">
            <span class="factor-name">engagement_score</span>
            <span class="factor-desc">阅读量、点赞、评论综合评分</span>
          </div>
          <div class="factor-item">
            <span class="factor-name">recency_bonus</span>
            <span class="factor-desc">文章发布时间越近 bonus 越高</span>
          </div>
          <div class="factor-item">
            <span class="factor-name">penalty</span>
            <span class="factor-desc">违规内容、降权记录等扣分</span>
          </div>
        </div>
      </div>

      <div class="config-right">
        <el-form :model="configForm" label-position="top" :disabled="!isAdmin">
          <div class="config-section card-static">
            <h4>Tier 间隔配置</h4>
            <el-form-item label="S 级间隔 (分钟)">
              <el-input-number v-model="configForm.tier_s_interval" :min="15" />
            </el-form-item>
            <el-form-item label="A 级间隔 (分钟)">
              <el-input-number v-model="configForm.tier_a_interval" :min="30" />
            </el-form-item>
            <el-form-item label="B 级间隔 (分钟)">
              <el-input-number v-model="configForm.tier_b_interval" :min="60" />
            </el-form-item>
            <el-form-item label="C 级间隔 (分钟)">
              <el-input-number v-model="configForm.tier_c_interval" :min="120" />
            </el-form-item>
          </div>

          <div class="config-section card-static">
            <h4>权重系数</h4>
            <el-form-item label="阅读量权重">
              <el-slider v-model="configForm.read_weight" :min="0" :max="2" :step="0.1" show-input />
            </el-form-item>
            <el-form-item label="点赞权重">
              <el-slider v-model="configForm.like_weight" :min="0" :max="2" :step="0.1" show-input />
            </el-form-item>
            <el-form-item label="评论权重">
              <el-slider v-model="configForm.comment_weight" :min="0" :max="2" :step="0.1" show-input />
            </el-form-item>
          </div>

          <div class="config-section card-static">
            <h4>阈值配置</h4>
            <el-form-item label="S 级阈值">
              <el-input-number v-model="configForm.tier_s_threshold" :min="0" :max="100" />
            </el-form-item>
            <el-form-item label="A 级阈值">
              <el-input-number v-model="configForm.tier_a_threshold" :min="0" :max="100" />
            </el-form-item>
            <el-form-item label="B 级阈值">
              <el-input-number v-model="configForm.tier_b_threshold" :min="0" :max="100" />
            </el-form-item>
          </div>

          <div class="action-buttons" v-if="isAdmin">
            <el-button type="primary" size="large" @click="handleSave">
              保存并重启调度
            </el-button>
            <el-button size="large" @click="showTestDialog = true">
              模拟测试
            </el-button>
          </div>
        </el-form>
      </div>
    </div>

    <el-dialog v-model="showTestDialog" title="模拟测试" width="500px">
      <el-form label-position="top">
        <el-form-item label="输入历史数据">
          <el-input
            v-model="testInput"
            type="textarea"
            :rows="4"
            placeholder='{"read_count": 10000, "like_count": 500, "comment_count": 100}'
          />
        </el-form-item>
        <div v-if="testResult" class="test-result">
          <el-tag type="success">新 Score: {{ testResult.score }}</el-tag>
          <el-tag>Tier: {{ testResult.tier }}</el-tag>
        </div>
      </el-form>
      <template #footer>
        <el-button @click="showTestDialog = false">关闭</el-button>
        <el-button type="primary" @click="handleTest">计算</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { usePermissions } from '@/composables/usePermissions'
import { getWeightConfig, updateWeightConfig, testWeightFormula } from '@/api/weight'

const { isAdmin } = usePermissions()

const showTestDialog = ref(false)
const testInput = ref('')
const testResult = ref(null)

const configForm = reactive({
  tier_s_interval: 15,
  tier_a_interval: 30,
  tier_b_interval: 60,
  tier_c_interval: 120,
  read_weight: 1.0,
  like_weight: 1.0,
  comment_weight: 1.0,
  tier_s_threshold: 80,
  tier_a_threshold: 60,
  tier_b_threshold: 40
})

onMounted(async () => {
  try {
    const response = await getWeightConfig()
    Object.assign(configForm, response.data)
  } catch (error) {
    console.error('Failed to load weight config:', error)
    ElMessage.warning('使用默认配置')
  }
})

async function handleSave() {
  try {
    await updateWeightConfig(configForm)
    ElMessage.success('配置已保存，调度正在重启')
  } catch (error) {
    ElMessage.error('保存失败')
  }
}

async function handleTest() {
  try {
    const inputData = JSON.parse(testInput.value)
    const response = await testWeightFormula(inputData)
    testResult.value = response.data
  } catch (error) {
    ElMessage.error('测试失败，请检查输入格式')
  }
}
</script>

<style lang="scss" scoped>
.weight-config {
  .page-header {
    margin-bottom: 24px;

    h2 {
      font-size: 20px;
      font-weight: 600;
      margin-bottom: 16px;
    }
  }

  .config-layout {
    display: grid;
    grid-template-columns: 40fr 60fr;
    gap: 24px;
  }

  .config-left {
    padding: 24px;
    position: sticky;
    top: 20px;

    h3 {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 16px;
    }
  }

  .formula-display {
    background: $color-bg;
    border-radius: $radius-sm;
    padding: 16px;
    margin-bottom: 24px;
  }

  .formula-text {
    font-family: 'Monaco', 'Menlo', monospace;
    font-size: 13px;
    line-height: 1.6;
    margin: 0;
    white-space: pre-wrap;
  }

  .factor-list {
    h4 {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 12px;
    }
  }

  .factor-item {
    display: flex;
    flex-direction: column;
    padding: 12px 0;
    border-bottom: 1px solid rgba(0, 0, 0, 0.05);

    &:last-child {
      border-bottom: none;
    }
  }

  .factor-name {
    font-family: monospace;
    font-size: 13px;
    font-weight: 500;
    color: $color-primary;
  }

  .factor-desc {
    font-size: 12px;
    color: $color-text-secondary;
    margin-top: 4px;
  }

  .config-right {
    display: flex;
    flex-direction: column;
    gap: 20px;
  }

  .config-section {
    padding: 20px;

    h4 {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 16px;
    }
  }

  .action-buttons {
    display: flex;
    gap: 12px;

    .el-button {
      flex: 1;
    }
  }

  .test-result {
    display: flex;
    gap: 12px;
    margin-top: 16px;
  }
}
</style>
