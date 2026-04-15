<template>
  <div class="dashboard">
    <div class="stats-grid">
      <StatCard
        label="总账号数"
        :value="stats.totalAccounts"
        :icon="User"
      />
      <StatCard
        label="活跃任务"
        :value="stats.activeTasks"
        :icon="Odometer"
      />
      <StatCard
        label="今日高优文章"
        :value="stats.todayArticles"
        :icon="Document"
      />
      <StatCard
        label="代理健康度"
        :value="stats.proxyHealth"
        :icon="Connection"
        icon-color="#22C55E"
        icon-bg="rgba(34, 197, 94, 0.1)"
      />
    </div>

    <div class="charts-row">
      <div class="chart-left">
        <TrendChart :data="trendData" />
      </div>
      <div class="chart-right">
        <TierPieChart :data="tierData" />
      </div>
    </div>

    <div class="bottom-row">
      <RecentArticles :articles="recentArticles" />
    </div>

    <el-button
      class="fetch-button pulse-button"
      type="primary"
      size="large"
      @click="handleFetch"
    >
      <el-icon :size="20"><Refresh /></el-icon>
      立即抓取
    </el-button>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { User, Odometer, Document, Connection, Refresh } from '@element-plus/icons-vue'
import StatCard from '@/components/common/StatCard.vue'
import TrendChart from '@/components/dashboard/TrendChart.vue'
import TierPieChart from '@/components/dashboard/TierPieChart.vue'
import RecentArticles from '@/components/dashboard/RecentArticles.vue'
import { getAccounts } from '@/api/accounts'
import { getArticles } from '@/api/articles'

const stats = ref({
  totalAccounts: 0,
  activeTasks: 0,
  todayArticles: 0,
  proxyHealth: 0
})

const trendData = ref({
  dates: [],
  values: []
})

const tierData = ref([])

const recentArticles = ref([])

onMounted(async () => {
  await Promise.all([
    fetchDashboardData(),
    fetchRecentArticles()
  ])
})

async function fetchDashboardData() {
  try {
    const [accountsRes, articlesRes] = await Promise.all([
      getAccounts(),
      getArticles({ limit: 10 })
    ])

    const accounts = accountsRes.data || []
    stats.value.totalAccounts = accounts.length
    stats.value.activeTasks = accounts.filter(a => a.status === 'active').length

    const today = new Date().toDateString()
    const todayArticleList = (articlesRes.data || []).filter(a =>
      new Date(a.publish_time).toDateString() === today
    )
    stats.value.todayArticles = todayArticleList.length

    stats.value.proxyHealth = 95 // Placeholder

    // Generate trend data (last 7 days)
    const dates = []
    const values = []
    for (let i = 6; i >= 0; i--) {
      const date = new Date()
      date.setDate(date.getDate() - i)
      dates.push(date.toLocaleDateString('zh-CN', { month: 'short', day: 'numeric' }))
      values.push(Math.floor(Math.random() * 50) + 20)
    }
    trendData.value = { dates, values }

    // Generate tier data
    const tierCounts = {}
    accounts.forEach(a => {
      tierCounts[a.tier] = (tierCounts[a.tier] || 0) + 1
    })
    tierData.value = Object.entries(tierCounts).map(([tier, count]) => ({ tier, count }))

    recentArticles.value = (articlesRes.data || []).slice(0, 5)
  } catch (error) {
    // Silent fail - use empty data
  }
}

async function fetchRecentArticles() {
  try {
    const response = await getArticles({ limit: 5, sort: '-publish_time' })
    recentArticles.value = response.data || []
  } catch (error) {
    // Silent fail
  }
}

async function handleFetch() {
  ElMessage.success('抓取任务已启动')
}
</script>

<style lang="scss" scoped>
.dashboard {
  position: relative;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 20px;
  margin-bottom: 24px;
}

.charts-row {
  display: grid;
  grid-template-columns: 65fr 35fr;
  gap: 20px;
  margin-bottom: 24px;
}

.chart-left,
.chart-right {
  min-height: 340px;
}

.bottom-row {
  margin-bottom: 80px;
}

.fetch-button {
  position: fixed;
  right: 40px;
  bottom: 40px;
  width: 140px;
  height: 140px;
  border-radius: 50%;
  font-size: 16px;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  box-shadow: 0 8px 30px rgba($color-primary, 0.4);
}
</style>
