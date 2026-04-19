<template>
  <V2Page
    title="今日监测控制台"
    watermark="DASHBOARD"
    action-rail="总览功能：抓取全部 / 查看实时队列 / 查看阻塞告警 / 代理健康 / AI JSON 失败 / 跳转作业日志"
  >
    <template #header-actions>
      <div class="v2-page-actions">
        <el-button type="warning" :loading="triggeringAll" @click="handleTriggerAll">立即抓取全部</el-button>
        <el-button @click="reload">刷新总览</el-button>
      </div>
    </template>

    <div class="v2-grid v2-grid-4">
      <V2MetricCard label="抓取账号健康" :value="`${healthyCollectors} / ${collectorAccounts.length}`" hint="normal / total" />
      <V2MetricCard label="监测对象" :value="monitoredAccounts.length" hint="含暂停与风险观察" />
      <V2MetricCard label="近 24h 新文章" :value="recentArticles" hint="已入库文章" />
      <V2MetricCard label="阻塞告警" :value="blockingAlerts" hint="代理 / AI / 作业" warm />
    </div>

    <div class="dashboard-grid">
      <V2Section title="每日抓取量" purple>
        <div class="chart-bars">
          <div v-for="item in dailyFetchChart" :key="item.label" class="chart-item">
            <i :style="{ height: `${item.height}px` }" />
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </V2Section>

      <V2Section title="分时段抓取量" purple>
        <div class="chart-bars compact">
          <div v-for="item in hourlyFetchChart" :key="item.label" class="chart-item">
            <i :style="{ height: `${item.height}px` }" />
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </div>
        </div>
      </V2Section>

      <V2Section title="实时作业队列" subtitle="失败分类、代理、账号和页码必须前置。">
        <div v-if="!fetchJobs.length">
          <V2Empty title="暂无作业" description="触发抓取或历史回填后会在这里显示。" />
        </div>
        <div v-else class="job-list">
          <article v-for="job in fetchJobs.slice(0, 5)" :key="job.id">
            <strong>{{ job.job_type || 'FETCH' }} · {{ job.status }}</strong>
            <span>account #{{ job.collector_account_id || '-' }} · proxy #{{ job.proxy_id || job.payload?.proxy_id || '-' }} · page {{ job.payload?.page || '-' }}</span>
            <em v-if="job.error || job.payload?.failure_category">{{ job.payload?.failure_category || job.error }}</em>
          </article>
        </div>
      </V2Section>

      <V2Section title="抓取账号健康">
        <div class="pill-row">
          <V2StatusPill label="正常" tone="success" />
          <strong>{{ collectorSummary.normal }}</strong>
          <V2StatusPill label="受限" tone="warning" />
          <strong>{{ collectorSummary.restricted }}</strong>
          <V2StatusPill label="失效" tone="danger" />
          <strong>{{ collectorSummary.invalid + collectorSummary.expired }}</strong>
        </div>
        <el-button class="section-link" @click="router.push('/capture-accounts')">查看抓取账号</el-button>
      </V2Section>

      <V2Section title="最新文章">
        <div class="article-mini-list">
          <article v-for="article in articles.slice(0, 5)" :key="article.id" @click="router.push(`/articles/${article.id}`)">
            <strong>{{ article.title }}</strong>
            <span>{{ article.account_name || article.author || '-' }} · {{ formatDateTime(article.published_at) }}</span>
          </article>
        </div>
      </V2Section>

      <V2Section title="代理与日志摘要">
        <div class="v2-grid v2-grid-2">
          <div class="summary-box">代理总数 <strong>{{ proxyStats.total || 0 }}</strong></div>
          <div class="summary-box">冷却中 <strong>{{ proxyStats.cooling || 0 }}</strong></div>
          <div class="summary-box">日志总数 <strong>{{ logStats.total || 0 }}</strong></div>
          <div class="summary-box">24h 失败 <strong>{{ logStats.failed_24h || logStats.failure_24h || 0 }}</strong></div>
        </div>
      </V2Section>
    </div>
  </V2Page>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import V2Empty from '@/components/v2/V2Empty.vue'
import V2MetricCard from '@/components/v2/V2MetricCard.vue'
import V2Page from '@/components/v2/V2Page.vue'
import V2Section from '@/components/v2/V2Section.vue'
import V2StatusPill from '@/components/v2/V2StatusPill.vue'
import { getArticles } from '@/api/articles'
import { getCollectorAccounts } from '@/api/collectorAccounts'
import { getFetchJobs } from '@/api/fetchJobs'
import { getLogStats } from '@/api/logs'
import { getMonitoredAccounts } from '@/api/monitoredAccounts'
import { getProxyStats } from '@/api/proxies'
import { triggerAllFetchTasks } from '@/api/tasks'
import { formatDateTime } from './helpers'

const router = useRouter()
const collectorAccounts = ref([])
const monitoredAccounts = ref([])
const articles = ref([])
const fetchJobs = ref([])
const proxyStats = ref({})
const logStats = ref({})
const triggeringAll = ref(false)

const healthyCollectors = computed(() => collectorAccounts.value.filter(item => item.health_status === 'normal').length)
const recentArticles = computed(() => articles.value.filter(item => item.published_at && Date.now() - new Date(item.published_at).getTime() < 86400000).length)
const blockingAlerts = computed(() => fetchJobs.value.filter(item => ['failed', 'blocked'].includes(item.status)).length + Number(proxyStats.value.cooling || 0))
const collectorSummary = computed(() => ({
  normal: collectorAccounts.value.filter(item => item.health_status === 'normal').length,
  restricted: collectorAccounts.value.filter(item => item.health_status === 'restricted').length,
  expired: collectorAccounts.value.filter(item => item.health_status === 'expired').length,
  invalid: collectorAccounts.value.filter(item => item.health_status === 'invalid').length
}))
const dailyFetchChart = computed(() => buildDailyFetchChart(fetchJobs.value))
const hourlyFetchChart = computed(() => buildHourlyFetchChart(fetchJobs.value))

onMounted(reload)

async function reload() {
  const [collectors, monitored, articleRes, jobs, proxies, logs] = await Promise.allSettled([
    getCollectorAccounts(),
    getMonitoredAccounts(),
    getArticles({ page: 1, page_size: 20 }),
    getFetchJobs(),
    getProxyStats(),
    getLogStats()
  ])
  collectorAccounts.value = collectors.value?.data?.items || []
  monitoredAccounts.value = monitored.value?.data?.items || []
  articles.value = articleRes.value?.data?.items || []
  fetchJobs.value = jobs.value?.data || []
  proxyStats.value = proxies.value?.data || {}
  logStats.value = logs.value?.data || {}
}

async function handleTriggerAll() {
  triggeringAll.value = true
  try {
    await triggerAllFetchTasks()
    ElMessage.success('已触发全部抓取')
    await reload()
  } finally {
    triggeringAll.value = false
  }
}

function buildDailyFetchChart(jobs) {
  const days = Array.from({ length: 7 }, (_, index) => {
    const date = new Date()
    date.setDate(date.getDate() - (6 - index))
    const key = date.toISOString().slice(0, 10)
    return { key, label: `${date.getMonth() + 1}/${date.getDate()}`, value: 0 }
  })
  const dayMap = Object.fromEntries(days.map(item => [item.key, item]))
  jobs.forEach(job => {
    const date = job.created_at ? new Date(job.created_at) : null
    if (!date || Number.isNaN(date.getTime())) return
    const key = date.toISOString().slice(0, 10)
    if (dayMap[key]) dayMap[key].value += 1
  })
  return withHeights(days)
}

function buildHourlyFetchChart(jobs) {
  const buckets = [
    { start: 6, end: 10, label: '06-10', value: 0 },
    { start: 10, end: 14, label: '10-14', value: 0 },
    { start: 14, end: 18, label: '14-18', value: 0 },
    { start: 18, end: 23, label: '18-23', value: 0 },
    { start: 23, end: 30, label: '23-06', value: 0 }
  ]
  jobs.forEach(job => {
    const date = job.created_at ? new Date(job.created_at) : null
    if (!date || Number.isNaN(date.getTime())) return
    let hour = date.getHours()
    if (hour < 6) hour += 24
    const bucket = buckets.find(item => hour >= item.start && hour < item.end)
    if (bucket) bucket.value += 1
  })
  return withHeights(buckets)
}

function withHeights(items) {
  const max = Math.max(1, ...items.map(item => item.value))
  return items.map(item => ({
    ...item,
    height: item.value > 0 ? Math.max(36, Math.round((item.value / max) * 190)) : 18
  }))
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.dashboard-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.55fr) minmax(340px, 0.85fr);
  gap: 24px;
  margin-top: 24px;
}

.chart-bars {
  height: 260px;
  display: flex;
  align-items: flex-end;
  gap: 18px;
  padding: 28px 16px 8px;

  &.compact {
    justify-content: space-around;
  }

  .chart-item {
    flex: 1 1 0;
    min-width: 54px;
    display: grid;
    justify-items: center;
    align-items: end;
    gap: 8px;
    color: rgba(#fff, 0.86);
    font-size: 12px;
    font-weight: 900;
  }

  i {
    display: block;
    width: min(48px, 80%);
    border-radius: 16px;
    background: $v2-yellow;
  }

  .chart-item:nth-child(even) i {
    background: rgba(#fff, 0.84);
  }

  strong {
    color: #fff;
    font-size: 16px;
  }
}

.job-list,
.article-mini-list {
  display: grid;
  gap: 12px;
}

.job-list article,
.article-mini-list article,
.summary-box {
  border-radius: 22px;
  background: $v2-card-soft;
  padding: 16px;
}

.job-list article {
  display: grid;
  gap: 4px;

  strong {
    color: $v2-ink;
  }

  span {
    color: $v2-muted;
    font-weight: 700;
  }

  em {
    color: $v2-orange;
    font-style: normal;
    font-weight: 900;
  }
}

.pill-row {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.section-link {
  margin-top: 18px;
}

.summary-box {
  color: $v2-muted;
  font-weight: 900;

  strong {
    display: block;
    color: $v2-purple;
    font-size: 28px;
  }
}

.article-mini-list article {
  cursor: pointer;
  display: grid;
  gap: 8px;

  strong {
    color: $v2-ink;
  }

  span {
    color: $v2-muted;
    font-size: 13px;
    font-weight: 700;
  }
}

@media (max-width: 1100px) {
  .dashboard-grid {
    grid-template-columns: 1fr;
  }
}
</style>
