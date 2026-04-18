<template>
  <V2Page
    title="公众号监测"
    subtitle="从公众号文章链接创建监测对象；解析 fakeid、能力标签、Feed、历史回填和 Tier 策略。"
    watermark="MONITORED"
    action-rail="监测功能：解析并创建 / 复制 RSS / 导出 OPML / 导出 CSV / 手动刷新 / 历史回填 / 停止回填 / 查看能力标签"
  >
    <template #header-actions>
      <div class="v2-page-actions">
        <el-select v-model="filterStatus" clearable placeholder="状态" style="width: 140px">
          <el-option label="监测中" value="monitoring" />
          <el-option label="暂停" value="paused" />
          <el-option label="风险观察" value="risk_observed" />
          <el-option label="失效" value="invalid" />
        </el-select>
        <el-button @click="handleExport('opml')">导出 OPML</el-button>
        <el-button @click="handleExport('csv')">导出 CSV</el-button>
        <el-button type="warning" :disabled="!canManageAccounts" @click="focusCreate">添加监测</el-button>
      </div>
    </template>

    <V2Section title="添加监测对象" subtitle="优先解析公众号链接；fakeid 不可得时明确 detail-only。">
      <div class="create-row">
        <el-input v-model="createForm.source_url" clearable placeholder="https://mp.weixin.qq.com/s?__biz=..." />
        <el-input v-model="createForm.name" clearable placeholder="名称（可选）" />
        <el-button type="primary" :loading="creating" :disabled="!canManageAccounts" @click="handleCreate">解析并创建</el-button>
        <el-button @click="copyAggregateFeed">复制聚合 Feed</el-button>
      </div>
    </V2Section>

    <div class="v2-grid v2-grid-4 stat-row">
      <V2MetricCard label="监测总数" :value="accounts.length" />
      <V2MetricCard label="监测中" :value="accounts.filter(item => item.status === 'monitoring').length" />
      <V2MetricCard label="仅详情抓取" :value="accounts.filter(isDetailOnly).length" warm />
      <V2MetricCard label="已排期" :value="accounts.filter(item => item.next_scheduled_at).length" />
    </div>

    <V2Section title="监测对象列表" subtitle="主操作露出；次级状态和能力放在展开信息里。">
      <div v-if="!filteredAccounts.length">
        <V2Empty title="暂无监测对象" description="输入一篇公众号文章链接，系统会解析公众号元数据并创建监测对象。" />
      </div>
      <div v-else class="account-list">
        <article v-for="account in filteredAccounts" :key="account.id" class="account-card">
          <div class="account-main">
            <div>
              <h3>{{ account.name || account.biz || `#${account.id}` }}</h3>
              <p v-if="account.mp_intro">{{ account.mp_intro }}</p>
              <div class="pill-line">
                <V2StatusPill :label="isDetailOnly(account) ? '仅详情抓取' : '列表+详情'" :tone="isDetailOnly(account) ? 'warning' : 'success'" />
                <V2StatusPill :label="account.fakeid ? `fakeid ${account.fakeid}` : 'fakeid 未解析'" :tone="account.fakeid ? 'purple' : 'warning'" />
                <V2StatusPill :label="`Tier ${account.tier || 3}`" tone="yellow" />
                <V2StatusPill :label="statusLabel(account.status)" :tone="account.status === 'monitoring' ? 'success' : 'warning'" />
              </div>
            </div>
            <div class="score-box">
              <strong>{{ Math.round(account.score || 0) }}</strong>
              <span>综合得分</span>
            </div>
          </div>
          <div class="meta-row">
            <span>抓取方式：{{ fetchModeLabel(account) }}</span>
            <span>下次抓取：{{ formatDateTime(account.next_scheduled_at) }}</span>
            <span>解析来源：{{ account.metadata_json?.resolve_source || '-' }}</span>
          </div>
          <div class="v2-button-row">
            <el-button size="small" @click="copyFeedUrl(account, 'rss')">复制 RSS</el-button>
            <el-button size="small" @click="copyFeedUrl(account, 'atom')">Atom</el-button>
            <el-button size="small" @click="copyFeedUrl(account, 'json')">JSON</el-button>
            <el-button size="small" :loading="fetchLoading[account.id]" :disabled="!canManageAccounts" @click="handleFetch(account)">立即抓取</el-button>
            <el-button size="small" :loading="backfillLoading[account.id]" :disabled="!canManageAccounts" @click="handleBackfill(account)">历史回填</el-button>
            <el-button size="small" @click="handleBackfillStatus(account)">回填状态</el-button>
            <el-button size="small" type="warning" :disabled="!canManageAccounts" @click="handleStopBackfill(account)">停止回填</el-button>
            <el-button size="small" @click="goToArticles(account)">文章</el-button>
            <el-button size="small" @click="openEdit(account)">编辑</el-button>
          </div>
        </article>
      </div>
    </V2Section>

    <el-dialog v-model="editDialog.visible" title="编辑监测对象" width="520px">
      <el-form label-position="top">
        <el-form-item label="公众号名称"><el-input v-model="editDialog.form.name" /></el-form-item>
        <el-form-item label="Fakeid"><el-input v-model="editDialog.form.fakeid" /></el-form-item>
        <el-form-item label="状态">
          <el-select v-model="editDialog.form.status" style="width: 100%">
            <el-option label="监测中" value="monitoring" />
            <el-option label="暂停" value="paused" />
            <el-option label="风险观察" value="risk_observed" />
            <el-option label="失效" value="invalid" />
          </el-select>
        </el-form-item>
        <el-form-item label="目标 Tier">
          <el-select v-model="editDialog.form.target_tier" style="width: 100%">
            <el-option v-for="tier in [1,2,3,4,5]" :key="tier" :label="`Tier ${tier}`" :value="tier" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="editDialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="savingEdit" @click="saveEdit">保存</el-button>
      </template>
    </el-dialog>
  </V2Page>
</template>

<script setup>
import { computed, onMounted, onUnmounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import V2Empty from '@/components/v2/V2Empty.vue'
import V2MetricCard from '@/components/v2/V2MetricCard.vue'
import V2Page from '@/components/v2/V2Page.vue'
import V2Section from '@/components/v2/V2Section.vue'
import V2StatusPill from '@/components/v2/V2StatusPill.vue'
import { usePermissions } from '@/composables/usePermissions'
import { useAuthStore } from '@/stores/auth'
import { exportFeeds } from '@/api/feeds'
import {
  createMonitoredAccount,
  getHistoryBackfillStatus,
  getMonitoredAccounts,
  stopHistoryBackfill,
  triggerHistoryBackfill,
  triggerMonitoredFetch,
  updateMonitoredAccount
} from '@/api/monitoredAccounts'
import { apiBaseUrl, downloadBlob, formatDateTime } from './helpers'

const router = useRouter()
const { canManageAccounts } = usePermissions()
const authStore = useAuthStore()
const loading = ref(false)
const creating = ref(false)
const savingEdit = ref(false)
const accounts = ref([])
const filterStatus = ref('')
const fetchLoading = ref({})
const backfillLoading = ref({})
const createForm = reactive({ source_url: '', name: '', fakeid: '' })
const editDialog = reactive({ visible: false, account: null, form: { name: '', fakeid: '', status: 'monitoring', target_tier: 3 } })

const filteredAccounts = computed(() => accounts.value.filter(item => !filterStatus.value || item.status === filterStatus.value))

onMounted(() => {
  loadAccounts()
  window.addEventListener('v2-open-monitored-create', focusCreate)
})
onUnmounted(() => window.removeEventListener('v2-open-monitored-create', focusCreate))

function focusCreate() {
  document.querySelector('.create-row')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

async function loadAccounts() {
  loading.value = true
  try {
    const response = await getMonitoredAccounts()
    accounts.value = response.data?.items || []
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!createForm.source_url.trim()) {
    ElMessage.warning('请先输入公众号链接')
    return
  }
  creating.value = true
  try {
    await createMonitoredAccount(createForm)
    ElMessage.success('监测对象创建成功')
    Object.assign(createForm, { source_url: '', name: '', fakeid: '' })
    await loadAccounts()
  } finally {
    creating.value = false
  }
}

async function handleFetch(account) {
  fetchLoading.value = { ...fetchLoading.value, [account.id]: true }
  try {
    await triggerMonitoredFetch(account.id)
    ElMessage.success('抓取任务已加入队列')
  } finally {
    fetchLoading.value = { ...fetchLoading.value, [account.id]: false }
  }
}

async function handleBackfill(account) {
  backfillLoading.value = { ...backfillLoading.value, [account.id]: true }
  try {
    await triggerHistoryBackfill(account.id)
    ElMessage.success('历史回填任务已加入队列')
  } finally {
    backfillLoading.value = { ...backfillLoading.value, [account.id]: false }
  }
}

async function handleBackfillStatus(account) {
  const response = await getHistoryBackfillStatus(account.id)
  const payload = response.data?.payload || {}
  ElMessage.info(`回填状态：${response.data?.status || 'idle'}，页码：${payload.page || '-'}，保存：${payload.saved_count || 0}`)
}

async function handleStopBackfill(account) {
  await stopHistoryBackfill(account.id)
  ElMessage.success('已请求停止历史回填')
}

function feedUrl(account, type = 'rss') {
  return account.feed_token ? `${apiBaseUrl()}/feeds/${account.feed_token}.${type}` : ''
}

async function copyFeedUrl(account, type = 'rss') {
  const url = feedUrl(account, type)
  if (!url) return
  await navigator.clipboard.writeText(url)
  ElMessage.success(`${type.toUpperCase()} 地址已复制`)
}

async function copyAggregateFeed() {
  const value = authStore.user?.aggregate_feed_token
  if (!value) {
    ElMessage.warning('当前用户未返回聚合 Feed token')
    return
  }
  await navigator.clipboard.writeText(`${apiBaseUrl()}/feeds/all/${value}.rss`)
  ElMessage.success('聚合 Feed 地址已复制')
}

async function handleExport(format) {
  const response = await exportFeeds(format)
  downloadBlob(response, `just-we-feeds.${format}`, format === 'opml' ? 'text/x-opml;charset=utf-8' : 'text/csv;charset=utf-8')
}

function openEdit(account) {
  editDialog.account = account
  editDialog.form = {
    name: account.name || '',
    fakeid: account.fakeid || '',
    status: account.status || 'monitoring',
    target_tier: account.tier || 3
  }
  editDialog.visible = true
}

async function saveEdit() {
  savingEdit.value = true
  try {
    await updateMonitoredAccount(editDialog.account.id, editDialog.form)
    editDialog.visible = false
    await loadAccounts()
  } finally {
    savingEdit.value = false
  }
}

function goToArticles(account) {
  router.push({ path: '/articles', query: { monitored_account_id: account.id } })
}

function isDetailOnly(account) {
  return Boolean(account.metadata_json?.capabilities?.detail_only)
}

function statusLabel(status) {
  return ({ monitoring: '监测中', paused: '暂停', risk_observed: '风险观察', invalid: '失效' })[status] || status || '-'
}

function fetchModeLabel(account) {
  const value = account.fetch_mode
  return ({ mp_admin: '公众号管理员', weread: '微信读书' })[value] || value || '-'
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.create-row {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(180px, 0.8fr) auto auto;
  gap: 12px;
}

.stat-row {
  margin: 24px 0;
}

.account-list {
  display: grid;
  gap: 16px;
}

.account-card {
  border-radius: 26px;
  background: $v2-card-soft;
  padding: 20px;
}

.account-main {
  display: flex;
  justify-content: space-between;
  gap: 18px;

  h3 {
    margin: 0 0 8px;
    font-size: 20px;
    font-weight: 950;
  }

  p {
    margin: 0 0 12px;
    color: $v2-muted;
    font-weight: 700;
  }
}

.pill-line,
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.meta-row {
  margin: 16px 0;
  color: $v2-muted;
  font-size: 13px;
  font-weight: 800;
}

.score-box {
  text-align: right;

  strong {
    color: $v2-purple;
    font-size: 36px;
    line-height: 1;
  }

  span {
    display: block;
    color: $v2-muted;
    font-weight: 800;
  }
}

@media (max-width: 900px) {
  .create-row {
    grid-template-columns: 1fr;
  }
}
</style>
