<template>
  <div class="article-list">
    <div class="page-header">
      <div>
        <h2>文章库</h2>
        <p>浏览已抓取文章，按监测对象、时间和 AI 相关度筛选。</p>
      </div>
      <div class="header-actions">
        <el-input v-model="searchQuery" clearable placeholder="搜索标题" style="width: 220px" />
        <el-select v-model="selectedMonitoredAccountId" clearable filterable placeholder="监测对象" style="width: 220px">
          <el-option
            v-for="account in monitoredAccounts"
            :key="account.id"
            :label="account.name"
            :value="account.id"
          />
        </el-select>
        <el-date-picker
          v-model="dateRange"
          type="daterange"
          range-separator="至"
          start-placeholder="开始日期"
          end-placeholder="结束日期"
          value-format="YYYY-MM-DD"
        />
      </div>
    </div>

    <div class="filter-bar card-static">
      <div class="slider-box">
        <span>AI 相关度</span>
        <el-slider v-model="relevanceRange" range :min="0" :max="100" />
      </div>
      <div class="filter-actions">
        <el-button @click="resetFilters">重置筛选</el-button>
        <el-button @click="loadArticles">刷新</el-button>
      </div>
    </div>

    <div class="table-card card-static">
      <el-table :data="displayArticles" v-loading="loading" empty-text="暂无文章">
        <el-table-column label="文章" min-width="280">
          <template #default="{ row }">
            <div class="article-cell">
              <img v-if="row.cover_image || row.images?.[0]" :src="row.cover_image || row.images?.[0]" class="cover-image">
              <div class="article-copy">
                <el-link type="primary" @click="router.push(`/articles/${row.id}`)">{{ row.title }}</el-link>
                <span class="article-url">{{ row.url }}</span>
              </div>
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="account_name" label="公众号" min-width="140" />
        <el-table-column prop="author" label="作者" width="120" />
        <el-table-column label="抓取通道" width="110">
          <template #default="{ row }">{{ row.fetch_mode || '-' }}</template>
        </el-table-column>
        <el-table-column label="AI 相关度" width="120">
          <template #default="{ row }">
            <el-tag :type="relevanceTagType(row.ai_relevance_ratio)">
              {{ row.ai_relevance_ratio !== null && row.ai_relevance_ratio !== undefined ? `${Math.round(row.ai_relevance_ratio * 100)}%` : '-' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="发布时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.published_at) }}</template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100]"
          :total="total"
          layout="total, sizes, prev, pager, next"
          @current-change="loadArticles"
          @size-change="loadArticles"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getArticles } from '@/api/articles'
import { getMonitoredAccounts } from '@/api/monitoredAccounts'

const route = useRoute()
const router = useRouter()

const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const articles = ref([])
const monitoredAccounts = ref([])

const searchQuery = ref('')
const selectedMonitoredAccountId = ref(route.query.monitored_account_id ? Number(route.query.monitored_account_id) : null)
const dateRange = ref([])
const relevanceRange = ref([0, 100])

const displayArticles = computed(() => {
  return articles.value.filter((item) => {
    if (searchQuery.value && !item.title.toLowerCase().includes(searchQuery.value.toLowerCase())) {
      return false
    }
    const ratio = Math.round((item.ai_relevance_ratio || 0) * 100)
    return ratio >= relevanceRange.value[0] && ratio <= relevanceRange.value[1]
  })
})

onMounted(async () => {
  await Promise.all([loadMonitoredAccounts(), loadArticles()])
})

watch(
  () => route.query.monitored_account_id,
  (value) => {
    selectedMonitoredAccountId.value = value ? Number(value) : null
    loadArticles()
  }
)

watch([selectedMonitoredAccountId, dateRange], () => {
  currentPage.value = 1
  loadArticles()
})

async function loadMonitoredAccounts() {
  try {
    const response = await getMonitoredAccounts()
    monitoredAccounts.value = response.data?.items || []
  } catch (error) {
    console.error('Failed to load monitored accounts:', error)
  }
}

async function loadArticles() {
  loading.value = true
  try {
    const response = await getArticles({
      page: currentPage.value,
      page_size: pageSize.value,
      monitored_account_id: selectedMonitoredAccountId.value || undefined,
      start_date: dateRange.value?.[0] || undefined,
      end_date: dateRange.value?.[1] || undefined
    })
    articles.value = response.data?.items || []
    total.value = response.data?.total || 0
  } finally {
    loading.value = false
  }
}

function resetFilters() {
  searchQuery.value = ''
  selectedMonitoredAccountId.value = null
  dateRange.value = []
  relevanceRange.value = [0, 100]
  currentPage.value = 1
  router.replace({ path: route.path, query: {} })
  loadArticles()
}

function relevanceTagType(value) {
  if (value >= 0.8) return 'success'
  if (value >= 0.5) return 'warning'
  return 'info'
}

function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
.article-list {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.page-header {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: flex-start;

  h2 {
    margin: 0 0 6px;
  }

  p {
    margin: 0;
    color: $color-text-secondary;
  }
}

.header-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.filter-bar,
.table-card {
  padding: 20px;
}

.filter-bar {
  display: flex;
  justify-content: space-between;
  gap: 16px;
  align-items: center;
}

.filter-actions {
  display: flex;
  gap: 8px;
}

.slider-box {
  display: flex;
  align-items: center;
  gap: 16px;
  flex: 1;
}

.article-cell {
  display: flex;
  gap: 12px;
  align-items: center;
}

.cover-image {
  width: 56px;
  height: 56px;
  border-radius: 10px;
  object-fit: cover;
  flex-shrink: 0;
}

.article-copy {
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.article-url {
  font-size: 12px;
  color: $color-text-secondary;
  overflow: hidden;
  text-overflow: ellipsis;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

@media (max-width: 768px) {
  .filter-bar,
  .slider-box,
  .filter-actions {
    flex-direction: column;
    align-items: stretch;
  }

  .article-cell {
    align-items: flex-start;
  }

  .pagination {
    justify-content: flex-start;
  }
}
</style>
