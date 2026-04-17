<template>
  <div class="capture-account-manage">
    <div class="page-header">
      <div>
        <h2>抓取账号管理</h2>
        <p>绑定用于列表抓取和详情抓取的 WeRead / 公众号后台账号，并关注健康状态。</p>
      </div>
      <div class="header-actions">
        <el-select v-model="filterType" clearable placeholder="账号类型" style="width: 160px">
          <el-option label="微信读书" value="weread" />
          <el-option label="公众号管理员" value="mp_admin" />
        </el-select>
        <el-select v-model="filterHealth" clearable placeholder="健康状态" style="width: 160px">
          <el-option label="正常" value="normal" />
          <el-option label="受限" value="restricted" />
          <el-option label="已过期" value="expired" />
          <el-option label="不可用" value="invalid" />
        </el-select>
        <el-button v-if="canManageAccounts" type="primary" @click="openAddDialog()">
          添加抓取账号
        </el-button>
      </div>
    </div>

    <div class="stats-grid">
      <StatCard label="账号总数" :value="accounts.length" :icon="Connection" />
      <StatCard label="健康账号" :value="healthyCount" :icon="CircleCheck" />
      <StatCard label="即将过期" :value="expiringSoonCount" :icon="Warning" />
      <StatCard label="最近失败" :value="failureCount" :icon="Monitor" />
    </div>

    <div class="table-card card-static">
      <el-table :data="filteredAccounts" v-loading="loading" empty-text="暂无抓取账号">
        <el-table-column prop="display_name" label="账号名称" min-width="180" />
        <el-table-column prop="external_id" label="外部标识" min-width="180" />
        <el-table-column label="类型" width="120">
          <template #default="{ row }">
            <el-tag :type="row.account_type === 'weread' ? 'success' : 'primary'">
              {{ row.account_type === 'weread' ? '微信读书' : '公众号管理员' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="健康状态" width="120">
          <template #default="{ row }">
            <el-tag :type="healthTagType(row.health_status)">
              {{ healthLabel(row.health_status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="风险状态" width="120">
          <template #default="{ row }">
            <el-tag :type="riskTagType(row.risk_status)">
              {{ row.risk_status }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column label="过期时间" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.expires_at) }}</template>
        </el-table-column>
        <el-table-column label="最后健康检查" min-width="180">
          <template #default="{ row }">{{ formatDateTime(row.last_health_check) }}</template>
        </el-table-column>
        <el-table-column label="最近异常" min-width="220">
          <template #default="{ row }">{{ row.risk_reason || '-' }}</template>
        </el-table-column>
        <el-table-column label="操作" width="220" fixed="right">
          <template #default="{ row }">
            <div v-if="canManageAccounts" class="table-actions">
              <el-button size="small" :loading="healthLoading[row.id]" @click="handleHealthCheck(row)">健康检查</el-button>
              <el-button size="small" @click="openAddDialog(row.account_type)">重新绑定</el-button>
              <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
            </div>
            <span v-else class="muted-placeholder">只读</span>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-dialog v-model="showAddDialog" title="绑定抓取账号" width="460px" :close-on-click-modal="false" @closed="resetDialog">
      <div v-if="!qrTicket" class="add-type-select">
        <el-radio-group v-model="selectedType">
          <el-radio-button label="weread">微信读书</el-radio-button>
          <el-radio-button label="mp_admin">公众号管理员</el-radio-button>
        </el-radio-group>
        <p class="dialog-help">生成二维码后，请用对应账号扫码确认，成功后系统会自动绑定。</p>
        <el-button type="primary" @click="createQRCode">生成二维码</el-button>
      </div>

      <div v-else class="qr-state">
        <img :src="qrUrl" alt="二维码" class="qr-image">
        <el-tag :type="qrStatusTagType(qrStatus)" size="large">{{ qrStatusLabel(qrStatus) }}</el-tag>
        <p class="dialog-help">有效期：{{ formatDateTime(qrExpireAt) }}</p>
        <p v-if="qrMessage" class="dialog-message">{{ qrMessage }}</p>
      </div>

      <template #footer>
        <el-button v-if="qrTicket" @click="refreshQRCode">刷新二维码</el-button>
        <el-button @click="closeDialog">关闭</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, Connection, Monitor, Warning } from '@element-plus/icons-vue'
import StatCard from '@/components/common/StatCard.vue'
import { usePermissions } from '@/composables/usePermissions'
import {
  cancelCollectorQRLogin,
  deleteCollectorAccount,
  generateCollectorQRCode,
  getCollectorAccounts,
  getCollectorQRStatus,
  healthCheckCollectorAccount
} from '@/api/collectorAccounts'
const { canManageAccounts } = usePermissions()

const loading = ref(false)
const accounts = ref([])
const filterType = ref('')
const filterHealth = ref('')
const healthLoading = ref({})

const showAddDialog = ref(false)
const selectedType = ref('mp_admin')
const qrTicket = ref('')
const qrUrl = ref('')
const qrStatus = ref('waiting')
const qrExpireAt = ref('')
const qrMessage = ref('')
let pollTimer = null

const filteredAccounts = computed(() => {
  return accounts.value.filter((item) => {
    if (filterType.value && item.account_type !== filterType.value) return false
    if (filterHealth.value && item.health_status !== filterHealth.value) return false
    return true
  })
})

const healthyCount = computed(() => accounts.value.filter((item) => item.health_status === 'normal').length)
const expiringSoonCount = computed(() => accounts.value.filter((item) => daysUntil(item.expires_at) !== null && daysUntil(item.expires_at) <= 2).length)
const failureCount = computed(() => accounts.value.filter((item) => item.last_failure_at).length)

onMounted(loadAccounts)
onBeforeUnmount(stopPolling)

async function loadAccounts() {
  loading.value = true
  try {
    const response = await getCollectorAccounts()
    accounts.value = response.data?.items || []
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.response?.data?.error || '抓取账号列表加载失败')
  } finally {
    loading.value = false
  }
}

async function handleHealthCheck(account) {
  healthLoading.value = { ...healthLoading.value, [account.id]: true }
  try {
    const response = await healthCheckCollectorAccount(account.id)
    accounts.value = accounts.value.map((item) => (item.id === account.id ? response.data : item))
    ElMessage.success(`健康检查完成：${healthLabel(response.data.health_status)}`)
  } finally {
    healthLoading.value = { ...healthLoading.value, [account.id]: false }
  }
}

async function handleDelete(account) {
  await ElMessageBox.confirm(`确定删除抓取账号“${account.display_name}”吗？`, '删除确认', { type: 'warning' })
  await deleteCollectorAccount(account.id)
  ElMessage.success('抓取账号已删除')
  await loadAccounts()
}

function openAddDialog(type = 'mp_admin') {
  selectedType.value = type
  showAddDialog.value = true
}

async function createQRCode() {
  try {
    const response = await generateCollectorQRCode(selectedType.value)
    qrTicket.value = response.data.ticket
    qrUrl.value = response.data.qr_url
    qrExpireAt.value = response.data.expire_at
    qrStatus.value = 'waiting'
    qrMessage.value = ''
    startPolling()
  } catch (error) {
    qrMessage.value = error?.response?.data?.detail || error?.response?.data?.error || '二维码生成失败'
    ElMessage.error(qrMessage.value)
  }
}

async function refreshQRCode() {
  if (qrTicket.value) {
    await cancelCollectorQRLogin(qrTicket.value)
  }
  stopPolling()
  qrTicket.value = ''
  await createQRCode()
}

function closeDialog() {
  showAddDialog.value = false
}

function resetDialog() {
  stopPolling()
  if (qrTicket.value) {
    cancelCollectorQRLogin(qrTicket.value).catch(() => {})
  }
  qrTicket.value = ''
  qrUrl.value = ''
  qrExpireAt.value = ''
  qrMessage.value = ''
  qrStatus.value = 'waiting'
}

function startPolling() {
  stopPolling()
  pollTimer = window.setInterval(checkQRStatus, 3000)
  checkQRStatus()
}

function stopPolling() {
  if (pollTimer) {
    window.clearInterval(pollTimer)
    pollTimer = null
  }
}

async function checkQRStatus() {
  if (!qrTicket.value) return
  try {
    const response = await getCollectorQRStatus(qrTicket.value)
    qrStatus.value = response.data.status
    qrMessage.value = response.data.message || ''
    if (response.data.status === 'confirmed') {
      ElMessage.success('抓取账号绑定成功')
      stopPolling()
      await loadAccounts()
      showAddDialog.value = false
    }
    if (response.data.status === 'expired') {
      stopPolling()
    }
  } catch (error) {
    qrMessage.value = error?.response?.data?.detail || error?.response?.data?.error || '二维码状态查询失败'
    stopPolling()
  }
}

function healthTagType(status) {
  if (status === 'normal') return 'success'
  if (status === 'restricted') return 'warning'
  return 'danger'
}

function healthLabel(status) {
  const map = {
    normal: '正常',
    restricted: '受限',
    expired: '已过期',
    invalid: '不可用'
  }
  return map[status] || status
}

function riskTagType(status) {
  if (status === 'normal') return 'info'
  if (status === 'cooling') return 'warning'
  return 'danger'
}

function qrStatusLabel(status) {
  const map = {
    waiting: '等待扫码',
    scanned: '已扫码，待确认',
    confirmed: '登录成功',
    expired: '二维码已过期'
  }
  return map[status] || status
}

function qrStatusTagType(status) {
  if (status === 'confirmed') return 'success'
  if (status === 'scanned') return 'warning'
  if (status === 'expired') return 'danger'
  return 'info'
}

function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}

function daysUntil(value) {
  if (!value) return null
  const diff = new Date(value).getTime() - Date.now()
  return Math.max(0, Math.ceil(diff / (24 * 60 * 60 * 1000)))
}
</script>

<style lang="scss" scoped>
.capture-account-manage {
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

.muted-placeholder {
  color: $color-text-secondary;
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

.add-type-select,
.qr-state {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 16px;
}

.dialog-help,
.dialog-message {
  margin: 0;
  text-align: center;
  color: $color-text-secondary;
}

.qr-image {
  width: 220px;
  height: 220px;
  object-fit: contain;
  border-radius: 16px;
  border: 1px solid rgba(0, 0, 0, 0.08);
  padding: 12px;
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
  .table-card {
    padding: 16px;
  }

  .qr-image {
    width: 180px;
    height: 180px;
  }
}
</style>
