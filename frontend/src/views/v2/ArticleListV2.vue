<template>
  <V2Page
    title="文章列表"
    subtitle="按公众号、AI 状态、内容类型、目标命中和标题关键词筛选文章。"
    watermark="ARTICLES"
    action-rail="文章列表功能：搜索 / 按公众号筛选 / AI 状态筛选 / 目标命中筛选 / 打开详情 / 打开原文 / 重跑 AI / 删除文章"
  >
    <template #header-actions>
      <div class="v2-page-actions">
        <el-button @click="resetFilters">重置筛选</el-button>
        <el-button type="warning" @click="loadArticles">同步文章</el-button>
      </div>
    </template>

    <V2Section title="筛选文章" subtitle="目标类型命中只接受“是/不是”，不再使用泛化相关度作为核心判断。">
      <div class="filters-grid">
        <el-input v-model="searchQuery" clearable placeholder="搜索标题关键词" />
        <el-select v-model="selectedMonitoredAccountId" clearable filterable placeholder="公众号">
          <el-option v-for="account in monitoredAccounts" :key="account.id" :label="account.name" :value="account.id" />
        </el-select>
        <el-select v-model="targetMatch" clearable placeholder="目标命中">
          <el-option label="是" value="是" />
          <el-option label="不是" value="不是" />
        </el-select>
        <el-select v-model="aiStatus" clearable placeholder="AI 状态">
          <el-option label="成功" value="success" />
          <el-option label="失败" value="failed" />
          <el-option label="等待" value="pending" />
          <el-option label="跳过" value="skipped" />
        </el-select>
        <el-select v-model="contentType" clearable placeholder="内容类型">
          <el-option label="普通文章" value="article" />
          <el-option label="图文消息" value="image_text" />
          <el-option label="纯图片" value="image_only" />
          <el-option label="短内容" value="short_content" />
          <el-option label="音频" value="audio" />
          <el-option label="视频" value="video" />
        </el-select>
        <el-date-picker v-model="dateRange" type="daterange" value-format="YYYY-MM-DD" start-placeholder="开始日期" end-placeholder="结束日期" />
      </div>
    </V2Section>

    <V2Section title="文章库" subtitle="卡片化行展示 AI 命中、抓取分类和关键操作。">
      <div v-if="!displayArticles.length && !loading">
        <V2Empty title="暂无文章" description="请先添加监测对象、触发抓取，或调整筛选条件。" />
      </div>
      <div v-else v-loading="loading" class="article-list">
        <article v-for="article in displayArticles" :key="article.id" class="article-card">
          <div class="article-main">
            <div class="article-copy">
              <h3 @click="router.push(`/articles/${article.id}`)">{{ article.title }}</h3>
              <p>{{ article.account_name || article.author || '-' }} · {{ formatDateTime(article.published_at) }}</p>
            </div>
            <el-button class="expand-card-button" @click="toggleArticleDetails(article.id)">{{ isExpanded(article.id) ? '收起' : '展开' }}</el-button>
          </div>
          <div v-if="isExpanded(article.id)" class="article-details">
            <div class="pill-line">
              <V2StatusPill :label="article.ai_target_match || '未判断'" :tone="article.ai_target_match === '是' ? 'success' : article.ai_target_match === '不是' ? 'neutral' : 'warning'" />
              <V2StatusPill :label="article.ai_analysis_status || 'AI 待处理'" :tone="article.ai_analysis_status === 'success' ? 'success' : article.ai_analysis_status === 'failed' ? 'danger' : 'warning'" />
              <V2StatusPill :label="contentTypeLabel(article.content_type)" tone="purple" />
              <V2StatusPill :label="article.metadata_json?.fetch_category || article.fetch_mode || '抓取分类未知'" tone="yellow" />
            </div>
            <div class="v2-button-row">
              <el-button size="small" @click="router.push(`/articles/${article.id}`)">详情</el-button>
              <el-button size="small" :disabled="!article.url" @click="openUrl(article.url)">原文</el-button>
              <el-button size="small" type="primary" :loading="reanalyzing[article.id]" @click="reanalyze(article)">重跑 AI</el-button>
              <el-button size="small" type="danger" plain :loading="deleting[article.id]" @click="removeArticle(article)">删除</el-button>
            </div>
          </div>
        </article>
      </div>
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
    </V2Section>
  </V2Page>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import V2Empty from '@/components/v2/V2Empty.vue'
import V2Page from '@/components/v2/V2Page.vue'
import V2Section from '@/components/v2/V2Section.vue'
import V2StatusPill from '@/components/v2/V2StatusPill.vue'
import { deleteArticle, getArticles, reanalyzeArticleAI } from '@/api/articles'
import { getMonitoredAccounts } from '@/api/monitoredAccounts'
import { formatDateTime } from './helpers'

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
const targetMatch = ref('')
const aiStatus = ref('')
const contentType = ref('')
const reanalyzing = ref({})
const deleting = ref({})
const expandedArticles = ref(new Set())

const displayArticles = computed(() => articles.value.filter(item => {
  if (searchQuery.value && !String(item.title || '').toLowerCase().includes(searchQuery.value.toLowerCase())) return false
  if (targetMatch.value && item.ai_target_match !== targetMatch.value) return false
  if (aiStatus.value && item.ai_analysis_status !== aiStatus.value) return false
  if (contentType.value && item.content_type !== contentType.value) return false
  return true
}))

onMounted(() => {
  loadMonitoredAccounts()
  loadArticles()
  window.addEventListener('v2-refresh-articles', loadArticles)
})
onUnmounted(() => window.removeEventListener('v2-refresh-articles', loadArticles))

watch([selectedMonitoredAccountId, dateRange], () => {
  currentPage.value = 1
  loadArticles()
})

async function loadMonitoredAccounts() {
  const response = await getMonitoredAccounts()
  monitoredAccounts.value = response.data?.items || []
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
  targetMatch.value = ''
  aiStatus.value = ''
  contentType.value = ''
  currentPage.value = 1
  router.replace({ path: route.path, query: {} })
  loadArticles()
}

async function reanalyze(article) {
  reanalyzing.value = { ...reanalyzing.value, [article.id]: true }
  try {
    await reanalyzeArticleAI(article.id)
    ElMessage.success('AI 分析已重跑')
    await loadArticles()
  } finally {
    reanalyzing.value = { ...reanalyzing.value, [article.id]: false }
  }
}

async function removeArticle(article) {
  await ElMessageBox.confirm(`确定删除文章“${article.title || article.id}”吗？`, '删除确认', { type: 'warning' })
  deleting.value = { ...deleting.value, [article.id]: true }
  try {
    await deleteArticle(article.id)
    ElMessage.success('文章已删除')
    await loadArticles()
  } finally {
    deleting.value = { ...deleting.value, [article.id]: false }
  }
}

function openUrl(url) {
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

function contentTypeLabel(value) {
  return ({ article: '普通文章', image_text: '图文消息', image_only: '纯图片', short_content: '短内容', audio: '音频', video: '视频', media_share: '媒体分享' })[value] || value || '未知类型'
}

function isExpanded(id) {
  return expandedArticles.value.has(id)
}

function toggleArticleDetails(id) {
  const next = new Set(expandedArticles.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedArticles.value = next
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.filters-grid {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.article-list {
  display: grid;
  gap: 16px;
  min-height: 180px;
}

.article-card {
  border-radius: 26px;
  background: $v2-card-soft;
  padding: 20px;
}

.article-main {
  display: flex;
  justify-content: space-between;
  gap: 22px;

  .article-copy {
    min-width: 0;
    flex: 1;
  }

  h3 {
    margin: 0 0 8px;
    font-size: 20px;
    font-weight: 950;
    cursor: pointer;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
    overflow-wrap: anywhere;
  }

  p {
    margin: 0 0 12px;
    color: $v2-muted;
    font-weight: 700;
  }
}

.expand-card-button {
  flex-shrink: 0;
}

.article-details {
  margin-top: 16px;
  display: grid;
  gap: 14px;
  border-radius: 20px;
  background: rgba(#fff, 0.45);
  padding: 16px;
}

.pill-line {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.pagination {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

@media (max-width: 900px) {
  .filters-grid {
    grid-template-columns: 1fr;
  }

  .article-main {
    flex-direction: column;
  }
}
</style>
