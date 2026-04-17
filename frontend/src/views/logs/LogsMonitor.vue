<template>
  <div class="logs-monitor">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="抓取作业" name="jobs" />
      <el-tab-pane label="操作审计" name="audit" />
    </el-tabs>

    <div v-if="activeTab === 'jobs'" class="panel card-static">
      <div class="panel-header">
        <h3>抓取作业</h3>
        <el-button @click="loadFetchJobs">刷新</el-button>
      </div>
      <el-table :data="fetchJobs" v-loading="jobsLoading" empty-text="暂无抓取作业">
        <el-table-column prop="job_type" label="任务类型" width="130" />
        <el-table-column prop="status" label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="jobTagType(row.status)">{{ row.status }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="monitored_account_id" label="监测对象 ID" width="130" />
        <el-table-column prop="collector_account_id" label="抓取账号 ID" width="130" />
        <el-table-column label="开始时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.started_at || row.created_at) }}</template>
        </el-table-column>
        <el-table-column label="结束时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.finished_at) }}</template>
        </el-table-column>
        <el-table-column label="错误" min-width="220">
          <template #default="{ row }">{{ row.error || '-' }}</template>
        </el-table-column>
        <el-table-column label="载荷" width="120">
          <template #default="{ row }">
            <el-button link @click="openDetail(row.payload)">查看</el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <div v-else class="panel card-static">
      <div class="panel-header">
        <h3>操作审计</h3>
        <div class="audit-filters">
          <el-input v-model="auditFilters.action" clearable placeholder="动作" style="width: 180px" @change="loadAuditLogs" />
          <el-input v-model="auditFilters.target_type" clearable placeholder="目标类型" style="width: 180px" @change="loadAuditLogs" />
          <el-button @click="loadAuditLogs">刷新</el-button>
        </div>
      </div>
      <el-table :data="auditLogs" v-loading="auditLoading" empty-text="暂无操作日志">
        <el-table-column prop="timestamp" label="时间" min-width="180" />
        <el-table-column prop="event" label="动作" width="160" />
        <el-table-column prop="target_type" label="目标类型" width="140" />
        <el-table-column prop="target_id" label="目标 ID" width="120" />
        <el-table-column prop="detail" label="详情" min-width="260" />
        <el-table-column label="结果" width="120">
          <template #default="{ row }">
            <el-tag :type="row.result === 'success' ? 'success' : row.result === 'failed' ? 'danger' : 'info'">
              {{ row.result }}
            </el-tag>
          </template>
        </el-table-column>
      </el-table>
      <div class="pagination">
        <el-pagination
          v-model:current-page="auditPage"
          v-model:page-size="auditPageSize"
          :page-sizes="[20, 50, 100]"
          :total="auditTotal"
          layout="total, sizes, prev, pager, next"
          @current-change="loadAuditLogs"
          @size-change="loadAuditLogs"
        />
      </div>
    </div>

    <el-dialog v-model="showPayloadDialog" title="作业载荷" width="680px">
      <pre class="payload-viewer">{{ JSON.stringify(selectedPayload, null, 2) }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { getFetchJobs } from '@/api/fetchJobs'
import { getLogs } from '@/api/logs'

const activeTab = ref('jobs')
const jobsLoading = ref(false)
const auditLoading = ref(false)
const fetchJobs = ref([])
const auditLogs = ref([])
const auditTotal = ref(0)
const auditPage = ref(1)
const auditPageSize = ref(20)
const showPayloadDialog = ref(false)
const selectedPayload = ref({})

const auditFilters = reactive({
  action: '',
  target_type: ''
})

onMounted(async () => {
  await Promise.all([loadFetchJobs(), loadAuditLogs()])
})

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
    const response = await getLogs({
      page: auditPage.value,
      page_size: auditPageSize.value,
      action: auditFilters.action || undefined,
      target_type: auditFilters.target_type || undefined
    })
    auditLogs.value = response.data?.items || []
    auditTotal.value = response.data?.total || 0
  } finally {
    auditLoading.value = false
  }
}

function openDetail(payload) {
  selectedPayload.value = payload || {}
  showPayloadDialog.value = true
}

function jobTagType(status) {
  if (status === 'success') return 'success'
  if (status === 'failed') return 'danger'
  if (status === 'running') return 'warning'
  return 'info'
}

function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
.logs-monitor {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.panel {
  padding: 20px;
}

.panel-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
  margin-bottom: 16px;

  h3 {
    margin: 0;
  }
}

.audit-filters {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

.payload-viewer {
  margin: 0;
  padding: 16px;
  background: $color-bg;
  border-radius: 12px;
  max-height: 420px;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 768px) {
  .panel {
    padding: 16px;
  }

  .panel-header,
  .audit-filters {
    flex-direction: column;
    align-items: stretch;
  }

  .pagination {
    justify-content: flex-start;
  }
}
</style>
