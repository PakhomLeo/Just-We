<template>
  <V2Page
    title="作业与日志"
    subtitle="失败分类、账号、代理、页码和 payload 前置，快速定位抓取问题。"
    watermark="JOBS"
    action-rail="作业日志功能：任务筛选 / 日志筛选 / 刷新 / 查看 payload / 停止历史回填 / 重试失败 / 失败分类定位"
  >
    <template #header-actions>
      <div class="v2-page-actions">
        <el-button @click="reload">刷新</el-button>
        <el-button type="warning" @click="activeTab = activeTab === 'jobs' ? 'audit' : 'jobs'">{{ activeTab === 'jobs' ? '看审计' : '看作业' }}</el-button>
      </div>
    </template>

    <div class="v2-grid v2-grid-4">
      <V2MetricCard label="日志总数" :value="stats.total || auditTotal || 0" />
      <V2MetricCard label="24h 成功" :value="stats.success_24h || 0" />
      <V2MetricCard label="24h 失败" :value="stats.failed_24h || stats.failure_24h || 0" warm />
      <V2MetricCard label="待处理" :value="fetchJobs.filter(item => item.status === 'pending' || item.status === 'running').length" />
    </div>

    <V2Section title="筛选与切换" subtitle="支持按作业和审计两条线排障。">
      <el-tabs v-model="activeTab">
        <el-tab-pane label="抓取作业" name="jobs" />
        <el-tab-pane label="操作审计" name="audit" />
      </el-tabs>
      <div class="filters-grid">
        <el-input v-model="auditFilters.action" clearable placeholder="动作" />
        <el-input v-model="auditFilters.target_type" clearable placeholder="目标类型" />
        <el-input v-model="auditFilters.monitored_account_id" clearable placeholder="监测对象 ID" />
        <el-button @click="reload">应用筛选</el-button>
      </div>
    </V2Section>

    <V2Section v-if="activeTab === 'jobs'" title="抓取作业" subtitle="失败定位字段前置显示。">
      <el-table :data="fetchJobs" v-loading="jobsLoading" empty-text="暂无抓取作业">
        <el-table-column prop="job_type" label="类型" width="145" />
        <el-table-column label="状态" width="110"><template #default="{ row }"><V2StatusPill :label="row.status" :tone="jobTone(row.status)" /></template></el-table-column>
        <el-table-column label="公众号" width="110"><template #default="{ row }">#{{ row.monitored_account_id || '-' }}</template></el-table-column>
        <el-table-column label="账号" width="90"><template #default="{ row }">#{{ row.collector_account_id || row.payload?.collector_account_id || '-' }}</template></el-table-column>
        <el-table-column label="代理" width="90"><template #default="{ row }">#{{ row.proxy_id || row.payload?.proxy_id || '-' }}</template></el-table-column>
        <el-table-column label="页码" width="90"><template #default="{ row }">{{ row.payload?.page || row.payload?.begin || '-' }}</template></el-table-column>
        <el-table-column label="抓取/保存" width="120"><template #default="{ row }">{{ row.payload?.fetched_count || 0 }} / {{ row.payload?.saved_count || 0 }}</template></el-table-column>
        <el-table-column label="失败分类" min-width="160"><template #default="{ row }">{{ row.payload?.failure_category || row.error || '-' }}</template></el-table-column>
        <el-table-column label="时间" min-width="170"><template #default="{ row }">{{ formatDateTime(row.started_at || row.created_at) }}</template></el-table-column>
        <el-table-column label="Payload" width="100"><template #default="{ row }"><el-button link @click="openPayload(row.payload)">查看</el-button></template></el-table-column>
      </el-table>
    </V2Section>

    <V2Section v-else title="操作审计" subtitle="记录用户动作、目标资源和结果。">
      <el-table :data="auditLogs" v-loading="auditLoading" empty-text="暂无操作日志">
        <el-table-column prop="timestamp" label="时间" min-width="170" />
        <el-table-column prop="event" label="动作" min-width="150" />
        <el-table-column prop="target_type" label="目标类型" width="130" />
        <el-table-column prop="target_id" label="目标 ID" width="110" />
        <el-table-column prop="detail" label="详情" min-width="260" />
        <el-table-column label="结果" width="110"><template #default="{ row }"><V2StatusPill :label="row.result || '-'" :tone="row.result === 'success' ? 'success' : row.result === 'failed' ? 'danger' : 'neutral'" /></template></el-table-column>
      </el-table>
      <div class="pagination">
        <el-pagination v-model:current-page="auditPage" v-model:page-size="auditPageSize" :page-sizes="[20,50,100]" :total="auditTotal" layout="total, sizes, prev, pager, next" @current-change="loadAuditLogs" @size-change="loadAuditLogs" />
      </div>
    </V2Section>

    <el-drawer v-model="payloadDrawer" title="格式化 Payload" size="560px">
      <pre class="v2-json">{{ jsonText(selectedPayload) }}</pre>
    </el-drawer>
  </V2Page>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import V2MetricCard from '@/components/v2/V2MetricCard.vue'
import V2Page from '@/components/v2/V2Page.vue'
import V2Section from '@/components/v2/V2Section.vue'
import V2StatusPill from '@/components/v2/V2StatusPill.vue'
import { getFetchJobs } from '@/api/fetchJobs'
import { getLogs, getLogStats, getLogsByMonitoredAccount } from '@/api/logs'
import { formatDateTime, jsonText } from './helpers'

const activeTab = ref('jobs')
const jobsLoading = ref(false)
const auditLoading = ref(false)
const fetchJobs = ref([])
const auditLogs = ref([])
const auditTotal = ref(0)
const auditPage = ref(1)
const auditPageSize = ref(20)
const payloadDrawer = ref(false)
const selectedPayload = ref({})
const stats = ref({})
const auditFilters = reactive({ action: '', target_type: '', monitored_account_id: '' })

onMounted(() => {
  reload()
  window.addEventListener('v2-refresh-logs', reload)
})
onUnmounted(() => window.removeEventListener('v2-refresh-logs', reload))

async function reload() {
  await Promise.all([loadFetchJobs(), loadAuditLogs(), loadStats()])
}

async function loadFetchJobs() {
  jobsLoading.value = true
  try {
    const response = await getFetchJobs()
    fetchJobs.value = response.data || []
  } finally {
    jobsLoading.value = false
  }
}

async function loadAuditLogs() {
  auditLoading.value = true
  try {
    const params = { page: auditPage.value, page_size: auditPageSize.value, action: auditFilters.action || undefined, target_type: auditFilters.target_type || undefined }
    const response = auditFilters.monitored_account_id
      ? await getLogsByMonitoredAccount(auditFilters.monitored_account_id, params)
      : await getLogs(params)
    auditLogs.value = response.data?.items || []
    auditTotal.value = response.data?.total || 0
  } finally {
    auditLoading.value = false
  }
}

async function loadStats() {
  const response = await getLogStats()
  stats.value = response.data || {}
}

function openPayload(payload) {
  selectedPayload.value = payload || {}
  payloadDrawer.value = true
}

function jobTone(status) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  return 'neutral'
}
</script>

<style lang="scss" scoped>
.filters-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 12px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 18px;
}

@media (max-width: 900px) {
  .filters-grid {
    grid-template-columns: 1fr;
  }
}
</style>
