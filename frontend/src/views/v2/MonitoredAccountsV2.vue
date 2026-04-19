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
            <div class="account-summary">
              <h3>{{ account.name || account.biz || `#${account.id}` }}</h3>
              <p v-if="account.mp_intro">{{ account.mp_intro }}</p>
              <div class="pill-line">
                <V2StatusPill :label="isDetailOnly(account) ? '仅详情抓取' : '列表+详情'" :tone="isDetailOnly(account) ? 'warning' : 'success'" />
                <V2StatusPill :label="tierLabel(account)" :tone="isManualTier(account) ? 'purple' : 'yellow'" />
                <V2StatusPill :label="statusLabel(account.status)" :tone="account.status === 'monitoring' ? 'success' : 'warning'" />
              </div>
            </div>
            <el-button class="expand-card-button" @click="toggleAccountDetails(account.id)">{{ isExpanded(account.id) ? '收起' : '展开' }}</el-button>
          </div>
          <div v-if="isExpanded(account.id)" class="account-details">
            <div class="details-grid">
              <span><strong>fakeid</strong>{{ account.fakeid || '未解析' }}</span>
              <span><strong>抓取方式</strong>{{ fetchModeLabel(account) }}</span>
              <span><strong>下次抓取</strong>{{ formatDateTime(account.next_scheduled_at) }}</span>
              <span><strong>解析来源</strong>{{ account.metadata_json?.resolve_source || '-' }}</span>
              <span><strong>回填状态</strong>{{ backfillStatusLabel(account) }}</span>
              <span><strong>综合得分</strong>{{ Math.round(account.score || 0) }}<em v-if="isManualTier(account)">手动锁定</em></span>
            </div>
            <div class="v2-button-row">
              <el-button size="small" @click="copyFeedUrl(account, 'rss')">复制 RSS</el-button>
              <el-button size="small" @click="copyFeedUrl(account, 'atom')">Atom</el-button>
              <el-button size="small" @click="copyFeedUrl(account, 'json')">JSON</el-button>
              <el-button size="small" :loading="fetchLoading[account.id]" :disabled="!canManageAccounts" @click="handleFetch(account)">立即抓取</el-button>
              <el-button size="small" :loading="backfillLoading[account.id]" :disabled="!canManageAccounts" @click="handleBackfill(account)">历史回填</el-button>
              <el-button size="small" type="warning" :disabled="!canManageAccounts" @click="handleStopBackfill(account)">停止回填</el-button>
              <el-button size="small" @click="goToArticles(account)">文章</el-button>
              <el-button size="small" @click="openEdit(account)">编辑</el-button>
              <el-button size="small" type="danger" plain :disabled="!canManageAccounts" @click="handleDelete(account)">删除</el-button>
            </div>
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
        <el-form-item label="目标 Tier（保存后手动锁定）">
          <el-select v-model="editDialog.form.target_tier" style="width: 100%">
            <el-option v-for="tier in [1,2,3,4,5]" :key="tier" :label="`Tier ${tier}`" :value="tier" />
          </el-select>
        </el-form-item>
        <div class="v2-risk-note">手动切换后，该公众号会固定使用所选 Tier，不再由综合得分自动调整；得分会以锁定状态展示。</div>
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
import { ElMessage, ElMessageBox } from 'element-plus'
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
  deleteMonitoredAccount,
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
const backfillStatuses = ref({})
const expandedAccounts = ref(new Set())
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
    loadBackfillStatuses()
  } finally {
    loading.value = false
  }
}

async function loadBackfillStatuses() {
  const results = await Promise.allSettled(accounts.value.map(async account => {
    const response = await getHistoryBackfillStatus(account.id)
    return [account.id, response.data]
  }))
  backfillStatuses.value = Object.fromEntries(
    results
      .filter(item => item.status === 'fulfilled')
      .map(item => item.value)
  )
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
    await refreshBackfillStatus(account)
  } finally {
    backfillLoading.value = { ...backfillLoading.value, [account.id]: false }
  }
}

async function refreshBackfillStatus(account) {
  const response = await getHistoryBackfillStatus(account.id)
  backfillStatuses.value = { ...backfillStatuses.value, [account.id]: response.data }
}

async function handleStopBackfill(account) {
  await stopHistoryBackfill(account.id)
  ElMessage.success('已请求停止历史回填')
  await refreshBackfillStatus(account)
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

async function handleDelete(account) {
  await ElMessageBox.confirm(`确定删除公众号“${account.name || account.biz || account.id}”吗？关联文章、通知和作业会一并清理。`, '删除公众号', { type: 'warning' })
  await deleteMonitoredAccount(account.id)
  ElMessage.success('公众号已删除')
  await loadAccounts()
}

function goToArticles(account) {
  router.push({ path: '/articles', query: { monitored_account_id: account.id } })
}

function isExpanded(id) {
  return expandedAccounts.value.has(id)
}

function toggleAccountDetails(id) {
  const next = new Set(expandedAccounts.value)
  if (next.has(id)) next.delete(id)
  else next.add(id)
  expandedAccounts.value = next
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

function isManualTier(account) {
  return Boolean(account.manual_override?.target_tier)
}

function tierLabel(account) {
  return `Tier ${account.tier || 3}${isManualTier(account) ? ' · 手动' : ''}`
}

function backfillStatusLabel(account) {
  const data = backfillStatuses.value[account.id]
  if (!data) return '未查询'
  const payload = data.payload || {}
  const status = ({ idle: '空闲', running: '运行中', completed: '完成', failed: '失败', stopped: '已停止', stop_requested: '停止中', already_running: '运行中' })[data.status] || data.status || '空闲'
  const page = payload.page || payload.current_page
  const saved = payload.saved_count ?? payload.saved ?? payload.total_saved
  const extras = []
  if (page) extras.push(`第 ${page} 页`)
  if (saved !== undefined) extras.push(`保存 ${saved}`)
  return extras.length ? `${status}（${extras.join('，')}）` : status
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
  border-radius: 24px;
  background: $v2-card-soft;
  padding: 20px;
}

.account-main {
  display: flex;
  justify-content: space-between;
  gap: 18px;
  align-items: flex-start;

  .account-summary {
    min-width: 0;
    flex: 1;
  }

  h3 {
    margin: 0 0 8px;
    font-size: 20px;
    font-weight: 950;
  }

  p {
    margin: 0 0 12px;
    color: $v2-muted;
    font-weight: 700;
    display: -webkit-box;
    -webkit-line-clamp: 2;
    -webkit-box-orient: vertical;
    overflow: hidden;
  }
}

.pill-line,
.meta-row {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.expand-card-button {
  flex-shrink: 0;
}

.account-details {
  margin-top: 18px;
  display: grid;
  gap: 16px;
  border-radius: 20px;
  background: rgba(#fff, 0.45);
  padding: 16px;
}

.details-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
  gap: 10px;

  span {
    min-width: 0;
    color: $v2-muted;
    font-size: 13px;
    font-weight: 800;
    word-break: break-word;
  }

  strong {
    display: block;
    margin-bottom: 4px;
    color: $v2-ink;
    font-size: 12px;
    font-weight: 950;
  }

  em {
    margin-left: 8px;
    color: $v2-orange;
    font-style: normal;
    font-weight: 950;
  }
}

.backfill-inline {
  color: $v2-purple;
  font-weight: 950;
}

@media (max-width: 900px) {
  .create-row {
    grid-template-columns: 1fr;
  }
}
</style>
