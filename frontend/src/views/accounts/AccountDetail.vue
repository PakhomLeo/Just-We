<template>
  <el-drawer
    :model-value="modelValue"
    :title="account?.name || '账号详情'"
    size="500px"
    @close="$emit('close')"
  >
    <div v-if="account" class="account-detail">
      <div class="detail-section">
        <h4>基本信息</h4>
        <div class="info-grid">
          <div class="info-item">
            <span class="label">Biz</span>
            <span class="value">{{ account.biz || '-' }}</span>
          </div>
          <div class="info-item">
            <span class="label">Tier</span>
            <StatusTag :tier="account.tier" />
          </div>
          <div class="info-item">
            <span class="label">Score</span>
            <span class="value">{{ account.score || 0 }}</span>
          </div>
          <div class="info-item">
            <span class="label">状态</span>
            <StatusTag :status="account.status" />
          </div>
        </div>
      </div>

      <div class="detail-section">
        <h4>抓取历史</h4>
        <p class="text-secondary">
          最后抓取: {{ account.last_crawl ? formatDate(account.last_crawl) : '从未' }}
        </p>
        <p class="text-secondary">
          下次间隔: {{ account.next_interval ? `${account.next_interval}分钟` : '-' }}
        </p>
      </div>

      <div class="detail-section">
        <h4>热度图 (90天)</h4>
        <div class="heatmap-placeholder">
          <div
            v-for="(day, index) in heatmapData"
            :key="index"
            class="heat-cell"
            :style="{ opacity: day / 100 }"
          />
        </div>
      </div>

      <div class="detail-section">
        <h4>Override 设置</h4>
        <el-form label-position="top" size="small">
          <el-form-item label="Tier Override">
            <el-select v-model="overrideTier" placeholder="选择 Tier" clearable>
              <el-option label="S" value="S" />
              <el-option label="A" value="A" />
              <el-option label="B" value="B" />
              <el-option label="C" value="C" />
            </el-select>
          </el-form-item>
          <el-form-item label="Score 调整">
            <el-input-number v-model="overrideScore" :min="-50" :max="50" />
          </el-form-item>
          <el-form-item>
            <el-button type="primary" size="small">保存 Override</el-button>
          </el-form-item>
        </el-form>
      </div>
    </div>
  </el-drawer>
</template>

<script setup>
import { ref, watch } from 'vue'
import StatusTag from '@/components/common/StatusTag.vue'

const props = defineProps({
  modelValue: Boolean,
  account: Object
})

defineEmits(['close'])

const overrideTier = ref('')
const overrideScore = ref(0)
const heatmapData = ref(Array(90).fill(0).map(() => Math.random() * 100))

watch(() => props.account, (newAccount) => {
  if (newAccount) {
    overrideTier.value = newAccount.override_tier || ''
    overrideScore.value = newAccount.override_score || 0
  }
}, { immediate: true })

function formatDate(date) {
  return new Date(date).toLocaleDateString('zh-CN')
}
</script>

<style lang="scss" scoped>
.account-detail {
  .detail-section {
    margin-bottom: 24px;

    h4 {
      font-size: 14px;
      font-weight: 600;
      margin-bottom: 12px;
      color: $color-text;
    }
  }

  .info-grid {
    display: grid;
    grid-template-columns: repeat(2, 1fr);
    gap: 12px;
  }

  .info-item {
    display: flex;
    flex-direction: column;
    gap: 4px;

    .label {
      font-size: 12px;
      color: $color-text-secondary;
    }

    .value {
      font-size: 14px;
      font-weight: 500;
    }
  }

  .text-secondary {
    font-size: 14px;
    color: $color-text-secondary;
    margin-bottom: 4px;
  }

  .heatmap-placeholder {
    display: grid;
    grid-template-columns: repeat(15, 1fr);
    gap: 2px;
  }

  .heat-cell {
    aspect-ratio: 1;
    background-color: $color-primary;
    border-radius: 2px;
  }
}
</style>
