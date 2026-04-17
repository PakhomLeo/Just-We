<template>
  <div class="mp-account-manage">
    <div class="page-header">
      <div>
        <h2>公众号监测</h2>
        <p>从公众号链接创建监测源，调整 Tier 和状态，并手动触发抓取。</p>
      </div>
      <div class="header-actions">
        <el-select v-model="filterStatus" clearable placeholder="监测状态" style="width: 140px">
          <el-option label="监测中" value="monitoring" />
          <el-option label="暂停" value="paused" />
          <el-option label="风险观察" value="risk_observed" />
          <el-option label="失效" value="invalid" />
        </el-select>
        <el-select v-model="filterTier" clearable placeholder="Tier" style="width: 120px">
          <el-option v-for="tier in [1, 2, 3, 4, 5]" :key="tier" :label="`Tier ${tier}`" :value="tier" />
        </el-select>
        <el-button v-if="canManageAccounts" type="primary" @click="showCreateDialog = true">添加监测对象</el-button>
      </div>
    </div>

    <div class="stats-grid">
      <StatCard label="监测总数" :value="accounts.length" :icon="Connection" />
      <StatCard label="监测中" :value="accounts.filter((item) => item.status === 'monitoring').length" :icon="CircleCheck" />
      <StatCard label="高优先 Tier1-2" :value="accounts.filter((item) => item.tier <= 2).length" :icon="Top" />
      <StatCard label="已排期" :value="scheduledCount" :icon="Clock" />
    </div>

    <div class="table-card card-static">
      <el-table :data="filteredAccounts" v-loading="loading" empty-text="暂无监测对象">
        <el-table-column prop="name" label="公众号名称" min-width="180" />
        <el-table-column prop="biz" label="Biz" min-width="170" />
        <el-table-column prop="fakeid" label="Fakeid" min-width="140" />
        <el-table-column label="Tier" width="90">
          <template #default="{ row }">
            <el-tag :type="row.tier <= 2 ? 'danger' : row.tier === 3 ? 'warning' : 'info'">Tier {{ row.tier }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="综合得分" width="120">
          <template #default="{ row }">{{ Math.round(row.score) }}</template>
        </el-table-column>
        <el-table-column prop="primary_fetch_mode" label="主通道" width="110" />
        <el-table-column prop="fallback_fetch_mode" label="兜底通道" width="110" />
        <el-table-column label="下次抓取" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.next_scheduled_at) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="120">
          <template #default="{ row }">
            <el-tag :type="statusTagType(row.status)">{{ statusLabel(row.status) }}</el-tag>
          </template>
        </el-table-column>
        <el-table-column label="操作" width="320" fixed="right">
          <template #default="{ row }">
            <div class="table-actions">
              <template v-if="canManageAccounts">
                <el-button size="small" :loading="fetchLoading[row.id]" @click="handleFetch(row)">立即抓取</el-button>
                <el-button size="small" @click="openEditDialog(row)">编辑</el-button>
                <el-button size="small" @click="openStrategyDialog(row)">调整策略</el-button>
              </template>
              <el-button size="small" @click="goToArticles(row)">文章</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showCreateDialog" title="添加监测对象" width="520px" @closed="resetCreateForm">
      <el-form :model="createForm" label-position="top">
        <el-form-item label="公众号链接">
          <el-input v-model="createForm.source_url" placeholder="https://mp.weixin.qq.com/s/..." />
        </el-form-item>
        <el-form-item label="名称（可选）">
          <el-input v-model="createForm.name" placeholder="不填时由后端自动生成" />
        </el-form-item>
        <el-form-item label="Fakeid（可选）">
          <el-input v-model="createForm.fakeid" placeholder="可留空" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreateDialog = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">创建</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showEditDialog" title="编辑监测对象" width="520px" @closed="editingAccount = null">
      <el-form :model="editForm" label-position="top">
        <el-form-item label="公众号名称">
          <el-input v-model="editForm.name" />
        </el-form-item>
        <el-form-item label="Fakeid">
          <el-input v-model="editForm.fakeid" />
        </el-form-item>
        <el-form-item label="监测状态">
          <el-select v-model="editForm.status" style="width: 100%">
            <el-option label="监测中" value="monitoring" />
            <el-option label="暂停" value="paused" />
            <el-option label="风险观察" value="risk_observed" />
            <el-option label="失效" value="invalid" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showEditDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingEdit" @click="handleSaveEdit">保存</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showStrategyDialog" title="调整抓取策略" width="520px" @closed="strategyAccount = null">
      <el-form :model="strategyForm" label-position="top">
        <el-form-item label="目标 Tier">
          <el-select v-model="strategyForm.target_tier" style="width: 100%">
            <el-option v-for="tier in [1, 2, 3, 4, 5]" :key="tier" :label="`Tier ${tier}`" :value="tier" />
          </el-select>
        </el-form-item>
        <el-form-item label="监测状态">
          <el-select v-model="strategyForm.status" style="width: 100%">
            <el-option label="监测中" value="monitoring" />
            <el-option label="暂停" value="paused" />
            <el-option label="风险观察" value="risk_observed" />
            <el-option label="失效" value="invalid" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showStrategyDialog = false">取消</el-button>
        <el-button type="primary" :loading="savingStrategy" @click="handleSaveStrategy">应用</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CircleCheck, Clock, Connection, Top } from '@element-plus/icons-vue'
import StatCard from '@/components/common/StatCard.vue'
import { usePermissions } from '@/composables/usePermissions'
import { createMonitoredAccount, getMonitoredAccounts, triggerMonitoredFetch, updateMonitoredAccount } from '@/api/monitoredAccounts'

const router = useRouter()
const { canManageAccounts } = usePermissions()
const loading = ref(false)
const creating = ref(false)
const savingEdit = ref(false)
const savingStrategy = ref(false)
const accounts = ref([])
const fetchLoading = ref({})
const filterStatus = ref('')
const filterTier = ref('')

const showCreateDialog = ref(false)
const showEditDialog = ref(false)
const showStrategyDialog = ref(false)
const editingAccount = ref(null)
const strategyAccount = ref(null)

const createForm = reactive({
  source_url: '',
  name: '',
  fakeid: ''
})

const editForm = reactive({
  name: '',
  fakeid: '',
  status: 'monitoring'
})

const strategyForm = reactive({
  target_tier: 3,
  status: 'monitoring'
})

const filteredAccounts = computed(() => {
  return accounts.value.filter((item) => {
    if (filterStatus.value && item.status !== filterStatus.value) return false
    if (filterTier.value && item.tier !== filterTier.value) return false
    return true
  })
})

const scheduledCount = computed(() => accounts.value.filter((item) => item.next_scheduled_at).length)

onMounted(loadAccounts)

async function loadAccounts() {
  loading.value = true
  try {
    const response = await getMonitoredAccounts()
    accounts.value = response.data?.items || []
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.response?.data?.error || '监测对象列表加载失败')
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  creating.value = true
  try {
    await createMonitoredAccount(createForm)
    ElMessage.success('监测对象创建成功')
    showCreateDialog.value = false
    resetCreateForm()
    await loadAccounts()
  } finally {
    creating.value = false
  }
}

function resetCreateForm() {
  createForm.source_url = ''
  createForm.name = ''
  createForm.fakeid = ''
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

function openEditDialog(account) {
  editingAccount.value = account
  editForm.name = account.name
  editForm.fakeid = account.fakeid || ''
  editForm.status = account.status
  showEditDialog.value = true
}

async function handleSaveEdit() {
  if (!editingAccount.value) return
  savingEdit.value = true
  try {
    await updateMonitoredAccount(editingAccount.value.id, editForm)
    ElMessage.success('监测对象已更新')
    showEditDialog.value = false
    await loadAccounts()
  } finally {
    savingEdit.value = false
  }
}

function openStrategyDialog(account) {
  strategyAccount.value = account
  strategyForm.target_tier = account.tier
  strategyForm.status = account.status
  showStrategyDialog.value = true
}

async function handleSaveStrategy() {
  if (!strategyAccount.value) return
  savingStrategy.value = true
  try {
    await updateMonitoredAccount(strategyAccount.value.id, strategyForm)
    ElMessage.success('抓取策略已更新')
    showStrategyDialog.value = false
    await loadAccounts()
  } finally {
    savingStrategy.value = false
  }
}

function goToArticles(account) {
  router.push({ path: '/articles', query: { monitored_account_id: account.id } })
}

function statusTagType(status) {
  if (status === 'monitoring') return 'success'
  if (status === 'paused') return 'info'
  if (status === 'risk_observed') return 'warning'
  return 'danger'
}

function statusLabel(status) {
  const map = {
    monitoring: '监测中',
    paused: '暂停',
    risk_observed: '风险观察',
    invalid: '失效'
  }
  return map[status] || status
}

function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
.mp-account-manage {
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
  gap: 12px;
  flex-wrap: wrap;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 20px;
}

.table-card {
  padding: 20px;
}

@media (max-width: 900px) {
  .page-header {
    flex-direction: column;
  }

  .stats-grid {
    grid-template-columns: 1fr 1fr;
  }
}

@media (max-width: 768px) {
  .table-card,
  .form-card {
    padding: 16px;
  }
}
</style>
