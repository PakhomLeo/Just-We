<template>
  <div class="logs-monitor">
    <el-tabs v-model="activeTab">
      <el-tab-pane label="抓取日志" name="crawl" />
      <el-tab-pane label="操作审计" name="audit" />
      <el-tab-pane label="AI 调用日志" name="ai" />
    </el-tabs>

    <div class="logs-layout">
      <div class="logs-table card-static">
        <el-table :data="logs" v-loading="loading" max-height="400" stripe>
          <el-table-column prop="timestamp" label="时间" width="160">
            <template #default="{ row }">
              {{ formatTime(row.timestamp) }}
            </template>
          </el-table-column>

          <el-table-column prop="account" label="账号" width="120" />

          <el-table-column prop="event" label="事件" width="120" />

          <el-table-column prop="result" label="结果" width="100">
            <template #default="{ row }">
              <el-tag :type="getResultType(row.result)" size="small">
                {{ row.result }}
              </el-tag>
            </template>
          </el-table-column>

          <el-table-column prop="duration" label="耗时" width="80">
            <template #default="{ row }">
              {{ row.duration }}ms
            </template>
          </el-table-column>

          <el-table-column prop="detail" label="详情" min-width="200">
            <template #default="{ row }">
              <el-button link @click="showDetail(row)">查看 JSON</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div class="pagination">
          <el-pagination
            v-model:current-page="currentPage"
            v-model:page-size="pageSize"
            :total="total"
            :page-sizes="[20, 50, 100]"
            layout="total, sizes, prev, pager, next"
            @size-change="handleSizeChange"
            @current-change="handleCurrentChange"
          />
        </div>
      </div>

      <div class="live-stream card-static">
        <div class="stream-header">
          <h4>实时日志流</h4>
          <el-tag :type="sseConnected ? 'success' : 'danger'" size="small">
            {{ sseConnected ? '已连接' : '未连接' }}
          </el-tag>
        </div>

        <el-scrollbar ref="scrollbarRef" class="stream-content">
          <div
            v-for="(log, index) in liveLogs"
            :key="index"
            class="log-line"
            :class="log.level"
          >
            <span class="log-time">{{ formatTime(log.timestamp) }}</span>
            <span class="log-message">{{ log.message }}</span>
          </div>
        </el-scrollbar>
      </div>
    </div>

    <el-dialog v-model="showJsonDialog" title="日志详情" width="600px">
      <pre class="json-viewer">{{ JSON.stringify(selectedLog, null, 2) }}</pre>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted, nextTick } from 'vue'
import { useSSE } from '@/composables/useSSE'
import { getLogs } from '@/api/logs'

const activeTab = ref('crawl')
const loading = ref(false)
const logs = ref([])
const liveLogs = ref([])
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const showJsonDialog = ref(false)
const selectedLog = ref({})
const scrollbarRef = ref(null)

const sseConnected = ref(false)

onMounted(async () => {
  await fetchLogs()
  startSSELiveStream()
})

const { connected, connect } = useSSE('/api/logs/stream', handleSSEMessage)
sseConnected.value = connected.value

function handleSSEMessage(data) {
  liveLogs.value.unshift({
    timestamp: new Date().toISOString(),
    message: data.message || data,
    level: data.level || 'info'
  })

  // Keep only last 100 logs
  if (liveLogs.value.length > 100) {
    liveLogs.value = liveLogs.value.slice(0, 100)
  }

  nextTick(() => {
    if (scrollbarRef.value) {
      scrollbarRef.value.setScrollTop(0)
    }
  })
}

function startSSELiveStream() {
  connect()
}

async function fetchLogs() {
  loading.value = true
  try {
    const response = await getLogs({
      type: activeTab.value,
      page: currentPage.value,
      page_size: pageSize.value
    })
    logs.value = response.data.items || response.data || []
    total.value = response.data.total || logs.value.length
  } finally {
    loading.value = false
  }
}

function handleSizeChange() {
  fetchLogs()
}

function handleCurrentChange() {
  fetchLogs()
}

function showDetail(log) {
  selectedLog.value = log
  showJsonDialog.value = true
}

function formatTime(timestamp) {
  return new Date(timestamp).toLocaleTimeString('zh-CN')
}

function getResultType(result) {
  const typeMap = {
    success: 'success',
    failed: 'danger',
    pending: 'warning'
  }
  return typeMap[result] || 'info'
}
</script>

<style lang="scss" scoped>
.logs-monitor {
  .logs-layout {
    display: grid;
    grid-template-columns: 1fr 360px;
    gap: 24px;
    margin-top: 20px;
  }

  .logs-table {
    padding: 20px;
  }

  .pagination {
    margin-top: 16px;
    display: flex;
    justify-content: flex-end;
  }

  .live-stream {
    position: sticky;
    top: 20px;
    padding: 20px;
    display: flex;
    flex-direction: column;
    height: 500px;
  }

  .stream-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 16px;

    h4 {
      font-size: 14px;
      font-weight: 600;
    }
  }

  .stream-content {
    flex: 1;
    background: #1e1e1e;
    border-radius: $radius-sm;
    padding: 12px;
  }

  .log-line {
    display: flex;
    gap: 8px;
    font-family: monospace;
    font-size: 12px;
    line-height: 1.8;
    color: #d4d4d4;

    &.error {
      color: #f48771;
    }

    &.warning {
      color: #dcdcaa;
    }

    &.success {
      color: #89d185;
    }
  }

  .log-time {
    color: #858585;
    flex-shrink: 0;
  }

  .json-viewer {
    background: #1e1e1e;
    color: #d4d4d4;
    padding: 16px;
    border-radius: $radius-sm;
    font-family: monospace;
    font-size: 13px;
    overflow: auto;
    max-height: 400px;
  }
}
</style>
