<template>
  <div class="dashboard">
    <div class="stats-grid">
      <StatCard label="抓取账号" :value="stats.collectorTotal" :icon="User" />
      <StatCard label="监测对象" :value="stats.monitoredTotal" :icon="Monitor" />
      <StatCard label="未读告警" :value="notificationsStore.unreadCount" :icon="Bell" />
      <StatCard label="近 24h 新文章" :value="stats.recentArticles" :icon="Document" />
    </div>

    <div class="action-bar card-static">
      <div>
        <h3>手动调度</h3>
        <p>立即触发全部监测对象抓取，结果会写入抓取作业列表。</p>
      </div>
      <el-button v-if="canManageAccounts" type="primary" :loading="triggeringAll" @click="handleTriggerAll">
        立即抓取全部监测对象
      </el-button>
    </div>

    <div class="dashboard-grid">
      <section class="panel card-static">
        <div class="panel-header">
          <h3>抓取账号健康概览</h3>
          <el-button text @click="router.push('/capture-accounts')">查看全部</el-button>
        </div>
        <div class="summary-grid">
          <div class="summary-item">
            <span>正常</span>
            <strong>{{ collectorSummary.normal }}</strong>
          </div>
          <div class="summary-item warning">
            <span>受限</span>
            <strong>{{ collectorSummary.restricted }}</strong>
          </div>
          <div class="summary-item danger">
            <span>失效/异常</span>
            <strong>{{ collectorSummary.expired + collectorSummary.invalid }}</strong>
          </div>
        </div>
        <el-table :data="collectorAccounts.slice(0, 5)" empty-text="暂无抓取账号">
          <el-table-column prop="display_name" label="账号" min-width="180" />
          <el-table-column prop="account_type" label="类型" width="120" />
          <el-table-column label="健康状态" width="120">
            <template #default="{ row }">
              <el-tag :type="healthTagType(row.health_status)">{{ healthLabel(row.health_status) }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="过期时间" min-width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.expires_at) }}
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel card-static">
        <div class="panel-header">
          <h3>监测对象分层</h3>
          <el-button text @click="router.push('/mp-accounts')">管理监测对象</el-button>
        </div>
        <div class="tier-chips">
          <el-tag v-for="tier in tierStats" :key="tier.tier" size="large" effect="plain">
            Tier {{ tier.tier }}: {{ tier.count }}
          </el-tag>
        </div>
        <el-table :data="monitoredAccounts.slice(0, 6)" empty-text="暂无监测对象">
          <el-table-column prop="name" label="公众号" min-width="180" />
          <el-table-column label="Tier" width="90">
            <template #default="{ row }">Tier {{ row.tier }}</template>
          </el-table-column>
          <el-table-column label="得分" width="100">
            <template #default="{ row }">{{ Math.round(row.score) }}</template>
          </el-table-column>
          <el-table-column label="下次抓取" min-width="180">
            <template #default="{ row }">
              {{ formatDateTime(row.next_scheduled_at) }}
            </template>
          </el-table-column>
          <el-table-column label="状态" width="120">
            <template #default="{ row }">
              <el-tag :type="row.status === 'monitoring' ? 'success' : 'warning'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel card-static">
        <div class="panel-header">
          <h3>最新文章</h3>
          <el-button text @click="router.push('/articles')">查看文章库</el-button>
        </div>
        <el-table :data="articles.slice(0, 8)" empty-text="暂无文章">
          <el-table-column prop="title" label="标题" min-width="260">
            <template #default="{ row }">
              <el-link type="primary" @click="router.push(`/articles/${row.id}`)">{{ row.title }}</el-link>
            </template>
          </el-table-column>
          <el-table-column prop="account_name" label="公众号" min-width="140" />
          <el-table-column label="AI 相关度" width="120">
            <template #default="{ row }">
              {{ row.ai_relevance_ratio ? `${Math.round(row.ai_relevance_ratio * 100)}%` : '-' }}
            </template>
          </el-table-column>
          <el-table-column label="发布时间" min-width="180">
            <template #default="{ row }">{{ formatDateTime(row.published_at) }}</template>
          </el-table-column>
        </el-table>
      </section>

      <section class="panel card-static">
        <div class="panel-header">
          <h3>最近抓取作业</h3>
          <el-button text @click="router.push('/logs')">查看作业与日志</el-button>
        </div>
        <el-table :data="fetchJobs.slice(0, 8)" empty-text="暂无抓取作业">
          <el-table-column prop="job_type" label="任务类型" width="120" />
          <el-table-column prop="status" label="状态" width="110">
            <template #default="{ row }">
              <el-tag :type="jobTagType(row.status)">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="monitored_account_id" label="监测对象 ID" width="130" />
          <el-table-column label="开始时间" min-width="180">
            <template #default="{ row }">{{ formatDateTime(row.started_at || row.created_at) }}</template>
          </el-table-column>
          <el-table-column label="错误" min-width="220">
            <template #default="{ row }">{{ row.error || '-' }}</template>
          </el-table-column>
        </el-table>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { Bell, Document, Monitor, User } from '@element-plus/icons-vue'
import StatCard from '@/components/common/StatCard.vue'
import { getArticles } from '@/api/articles'
import { getCollectorAccounts } from '@/api/collectorAccounts'
import { getFetchJobs } from '@/api/fetchJobs'
import { getMonitoredAccounts } from '@/api/monitoredAccounts'
import { triggerAllFetchTasks } from '@/api/tasks'
import { usePermissions } from '@/composables/usePermissions'
import { useNotificationsStore } from '@/stores/notifications'

const router = useRouter()
const notificationsStore = useNotificationsStore()
const { canManageAccounts } = usePermissions()

const collectorAccounts = ref([])
const monitoredAccounts = ref([])
const articles = ref([])
const fetchJobs = ref([])
const triggeringAll = ref(false)

const stats = computed(() => {
  const recentArticles = articles.value.filter((item) => {
    if (!item.published_at) return false
    return Date.now() - new Date(item.published_at).getTime() <= 24 * 60 * 60 * 1000
  }).length

  return {
    collectorTotal: collectorAccounts.value.length,
    monitoredTotal: monitoredAccounts.value.length,
    recentArticles
  }
})

const collectorSummary = computed(() => ({
  normal: collectorAccounts.value.filter((item) => item.health_status === 'normal').length,
  restricted: collectorAccounts.value.filter((item) => item.health_status === 'restricted').length,
  expired: collectorAccounts.value.filter((item) => item.health_status === 'expired').length,
  invalid: collectorAccounts.value.filter((item) => item.health_status === 'invalid').length
}))

const tierStats = computed(() => {
  const map = monitoredAccounts.value.reduce((acc, item) => {
    const tier = item.tier || item.current_tier || 3
    acc[tier] = (acc[tier] || 0) + 1
    return acc
  }, {})
  return Object.entries(map).map(([tier, count]) => ({ tier, count }))
})

onMounted(async () => {
  try {
    await Promise.all([
      loadCollectors(),
      loadMonitoredAccounts(),
      loadArticles(),
      loadFetchJobs(),
      notificationsStore.fetchNotifications()
    ])
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.response?.data?.error || '仪表盘数据加载失败')
  }
})

async function loadCollectors() {
  const response = await getCollectorAccounts()
  collectorAccounts.value = response.data?.items || []
}

async function loadMonitoredAccounts() {
  const response = await getMonitoredAccounts()
  monitoredAccounts.value = response.data?.items || []
}

async function loadArticles() {
  const response = await getArticles({ page: 1, page_size: 20 })
  articles.value = response.data?.items || []
}

async function loadFetchJobs() {
  const response = await getFetchJobs()
  fetchJobs.value = response.data || []
}

async function handleTriggerAll() {
  triggeringAll.value = true
  try {
    await triggerAllFetchTasks()
    ElMessage.success('已触发全部监测对象抓取任务')
    await loadFetchJobs()
  } finally {
    triggeringAll.value = false
  }
}

function healthTagType(status) {
  if (status === 'normal') return 'success'
  if (status === 'restricted') return 'warning'
  return 'danger'
}

function healthLabel(status) {
  const mapping = {
    normal: '正常',
    restricted: '受限',
    expired: '已过期',
    invalid: '不可用'
  }
  return mapping[status] || status
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
.dashboard {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
}

.action-bar {
  padding: 20px 24px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 24px;

  h3 {
    margin: 0 0 4px;
  }

  p {
    margin: 0;
    color: $color-text-secondary;
  }
}

.dashboard-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 24px;
}

.panel {
  padding: 20px;
}

.panel-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 16px;

  h3 {
    margin: 0;
    font-size: 16px;
  }
}

.summary-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.summary-item {
  background: rgba($color-primary, 0.06);
  border-radius: 12px;
  padding: 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;

  strong {
    font-size: 22px;
  }

  &.warning {
    background: rgba(245, 158, 11, 0.12);
  }

  &.danger {
    background: rgba(239, 68, 68, 0.12);
  }
}

.tier-chips {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;
}

@media (max-width: 1200px) {
  .stats-grid,
  .dashboard-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .stats-grid,
  .dashboard-grid {
    grid-template-columns: 1fr;
  }

  .summary-grid {
    grid-template-columns: 1fr;
  }

  .action-bar {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
