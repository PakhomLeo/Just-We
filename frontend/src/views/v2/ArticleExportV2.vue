<template>
  <V2Page
    title="文章数据导出"
    subtitle="把已抓取文章的正文、图片、来源、公众号信息和 AI 阶段结果打包为 JSON 文件。"
    watermark="EXPORT"
  >
    <template #header-actions>
      <div class="v2-page-actions">
        <el-button @click="loadRecords">刷新记录</el-button>
        <el-button type="warning" :loading="exporting" @click="handleExport">生成 JSON</el-button>
      </div>
    </template>

    <div class="export-grid">
      <V2Section title="导出配置" subtitle="默认跳过已导出的文章；需要重跑全量时开启“包含已导出”。">
        <el-form label-position="top">
          <el-form-item label="导出范围">
            <el-segmented v-model="form.scope" :options="scopeOptions" />
          </el-form-item>
          <el-form-item v-if="form.scope === 'account'" label="选择公众号">
            <el-select v-model="form.monitored_account_id" filterable placeholder="选择账号">
              <el-option v-for="account in monitoredAccounts" :key="account.id" :label="account.name" :value="account.id" />
            </el-select>
          </el-form-item>
          <el-form-item v-if="form.scope === 'time'" label="发布时间范围">
            <el-date-picker
              v-model="dateRange"
              type="datetimerange"
              value-format="YYYY-MM-DDTHH:mm:ss"
              start-placeholder="开始时间"
              end-placeholder="结束时间"
            />
          </el-form-item>
          <div class="export-control-grid">
            <label class="export-field">
              <span>目标类型</span>
              <el-select v-model="form.target_match">
                <el-option label="全部" value="all" />
                <el-option label="符合目标类型" value="matched" />
                <el-option label="不符合目标类型" value="unmatched" />
                <el-option label="未判断" value="unknown" />
              </el-select>
            </label>
            <label class="export-field switch-field">
              <span>包含已导出</span>
              <el-switch v-model="form.include_exported" />
            </label>
          </div>
          <div class="export-note">
            全部导出完成后会记录文章 ID。下次未开启“包含已导出”时，会自动跳过这些文章，只导出新增内容。
          </div>
        </el-form>
      </V2Section>

      <V2Section title="JSON 内容说明" purple>
        <div class="schema-list">
          <article>
            <strong>metadata</strong>
            <span>导出时间、筛选条件、文章数量和版本号。</span>
          </article>
          <article>
            <strong>articles[]</strong>
            <span>标题、正文、富文本、原文链接、封面图、正文图片、抓取元数据。</span>
          </article>
          <article>
            <strong>account</strong>
            <span>公众号名称、biz、fakeid、头像、简介、Tier 和抓取方式。</span>
          </article>
          <article>
            <strong>ai</strong>
            <span>文字解析、图片解析、类型判断、合并结果、目标命中状态和错误信息。</span>
          </article>
        </div>
      </V2Section>
    </div>

    <V2Section title="导出记录" subtitle="每次导出都会留下记录，可重复下载历史 JSON 文件。">
      <div v-if="!records.length && !loading" class="empty-records">
        <V2Empty title="暂无导出记录" description="设置条件后生成第一个 JSON 导出文件。" />
      </div>
      <div v-else v-loading="loading" class="record-list">
        <article v-for="record in records" :key="record.id" class="record-card">
          <div>
            <strong>{{ scopeLabel(record.scope) }} · {{ targetLabel(record.target_match) }}</strong>
            <p>{{ formatDateTime(record.created_at) }} · {{ record.article_count }} 篇 · {{ record.file_name }}</p>
          </div>
          <div class="record-meta">
            <V2StatusPill :label="record.include_exported ? '包含已导出' : '跳过已导出'" :tone="record.include_exported ? 'warning' : 'success'" />
            <el-button size="small" type="primary" :disabled="record.status !== 'completed'" @click="download(record)">下载 JSON</el-button>
          </div>
        </article>
      </div>
    </V2Section>
  </V2Page>
</template>

<script setup>
import { onMounted, reactive, ref, watch } from 'vue'
import { ElMessage } from 'element-plus'
import V2Empty from '@/components/v2/V2Empty.vue'
import V2Page from '@/components/v2/V2Page.vue'
import V2Section from '@/components/v2/V2Section.vue'
import V2StatusPill from '@/components/v2/V2StatusPill.vue'
import { createArticleExport, downloadArticleExport, getArticleExports } from '@/api/articleExports'
import { getMonitoredAccounts } from '@/api/monitoredAccounts'
import { downloadBlob, formatDateTime } from './helpers'

const loading = ref(false)
const exporting = ref(false)
const records = ref([])
const monitoredAccounts = ref([])
const dateRange = ref([])
const form = reactive({
  scope: 'all',
  monitored_account_id: null,
  target_match: 'all',
  include_exported: false,
  start_date: null,
  end_date: null
})

const scopeOptions = [
  { label: '全部导出', value: 'all' },
  { label: '按账号', value: 'account' },
  { label: '按时间', value: 'time' }
]

onMounted(async () => {
  await Promise.all([loadAccounts(), loadRecords()])
})

watch(dateRange, value => {
  form.start_date = value?.[0] || null
  form.end_date = value?.[1] || null
})

watch(() => form.scope, scope => {
  if (scope !== 'account') form.monitored_account_id = null
  if (scope !== 'time') {
    dateRange.value = []
    form.start_date = null
    form.end_date = null
  }
})

async function loadAccounts() {
  const response = await getMonitoredAccounts()
  monitoredAccounts.value = response.data?.items || []
}

async function loadRecords() {
  loading.value = true
  try {
    const response = await getArticleExports({ limit: 50 })
    records.value = response.data?.items || []
  } finally {
    loading.value = false
  }
}

async function handleExport() {
  exporting.value = true
  try {
    const response = await createArticleExport({ ...form })
    const record = response.data
    ElMessage.success(`已生成 JSON：${record.article_count} 篇文章`)
    await loadRecords()
    if (record.article_count > 0) await download(record)
  } finally {
    exporting.value = false
  }
}

async function download(record) {
  const response = await downloadArticleExport(record.id)
  downloadBlob(response, record.file_name, 'application/json;charset=utf-8')
}

function scopeLabel(value) {
  return ({ all: '全部导出', account: '按账号导出', time: '按时间导出' })[value] || value
}

function targetLabel(value) {
  return ({ all: '全部文章', matched: '符合目标类型', unmatched: '不符合目标类型', unknown: '未判断' })[value] || value
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.export-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.15fr) minmax(320px, 0.85fr);
  gap: 24px;
}

.export-control-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(min(100%, 260px), 1fr));
  gap: 12px;
}

.export-field {
  min-height: 66px;
  border-radius: 22px;
  background: $v2-card-soft;
  padding: 12px 14px;
  display: grid;
  gap: 8px;
  align-content: center;

  span {
    color: $v2-muted;
    font-weight: 900;
  }

  :deep(.el-select) {
    width: 100%;
  }
}

.switch-field {
  grid-template-columns: 1fr auto;
  align-items: center;
}

.export-note {
  margin-top: 14px;
  border-radius: 20px;
  background: $v2-warning-bg;
  color: $v2-orange;
  padding: 14px 16px;
  font-weight: 900;
  line-height: 1.6;
}

.schema-list {
  display: grid;
  gap: 12px;

  article {
    border-radius: 20px;
    background: rgba(#fff, 0.18);
    padding: 14px 16px;
    color: rgba(#fff, 0.84);
    display: grid;
    gap: 6px;
  }

  strong {
    color: #fff;
    font-size: 18px;
  }
}

.record-list {
  display: grid;
  gap: 14px;
  min-height: 160px;
}

.record-card {
  border-radius: 24px;
  background: $v2-card-soft;
  padding: 18px;
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;

  strong {
    color: $v2-ink;
    font-size: 18px;
  }

  p {
    margin: 8px 0 0;
    color: $v2-muted;
    font-weight: 800;
  }
}

.record-meta {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
  justify-content: flex-end;
}

@media (max-width: 900px) {
  .export-grid {
    grid-template-columns: 1fr;
  }

  .record-card {
    align-items: stretch;
    flex-direction: column;
  }

  .record-meta {
    justify-content: flex-start;
  }
}
</style>
