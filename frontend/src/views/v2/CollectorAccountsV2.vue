<template>
  <V2Page
    title="抓取账号"
    subtitle="绑定 WeRead / 公众号管理员账号；二维码状态、登录代理锁定和 fakeid 发现都在页面内闭环。"
    watermark="CAPTURE"
    action-rail="账号功能：生成二维码 / 刷新二维码 / 轮询扫码状态 / 完成登录 / 发现 fakeid / 健康检查 / 更换登录代理 / 删除"
  >
    <template #header-actions>
      <div class="v2-page-actions">
        <el-select v-model="filterType" clearable placeholder="账号类型" style="width: 150px">
          <el-option label="公众号管理员" value="mp_admin" />
          <el-option label="微信读书" value="weread" />
        </el-select>
        <el-select v-model="filterHealth" clearable placeholder="健康状态" style="width: 150px">
          <el-option label="正常" value="normal" />
          <el-option label="受限" value="restricted" />
          <el-option label="已过期" value="expired" />
          <el-option label="不可用" value="invalid" />
        </el-select>
        <el-button type="warning" :disabled="!canManageAccounts" @click="focusCreate">新增账号</el-button>
      </div>
    </template>

    <div class="v2-grid v2-grid-4">
      <V2MetricCard label="账号总数" :value="accounts.length" />
      <V2MetricCard label="健康账号" :value="healthyCount" />
      <V2MetricCard label="即将过期" :value="expiringSoonCount" warm />
      <V2MetricCard label="最近失败" :value="failureCount" warm />
    </div>

    <div class="capture-grid">
      <V2Section title="绑定抓取账号" subtitle="mp_admin 登录必须选择长期代理；WeRead 可使用平台二维码。">
        <div class="type-switch">
          <button :class="{ active: selectedType === 'mp_admin' }" @click="selectedType = 'mp_admin'">公众号管理员</button>
          <button :class="{ active: selectedType === 'weread' }" @click="selectedType = 'weread'">微信读书</button>
        </div>
        <label v-if="selectedType === 'mp_admin'" class="field">
          <span>登录代理</span>
          <el-select v-model="selectedLoginProxyId" filterable placeholder="选择静态/粘性登录代理">
            <el-option
              v-for="proxy in loginProxies"
              :key="proxy.id"
              :label="loginProxyLabel(proxy)"
              :value="proxy.id"
            />
          </el-select>
        </label>
        <div v-if="selectedType === 'mp_admin'" class="v2-risk-note">
          登录代理用于维护公众号后台会话，登录成功后不会自动切换；更换代理会使当前凭证失效，需要重新扫码。
        </div>
        <div class="qr-box">
          <img v-if="qrUrl" :src="qrUrl" alt="二维码">
          <span v-else>QR</span>
        </div>
        <div class="qr-state-row">
          <V2StatusPill :label="qrStatusLabel(qrStatus)" :tone="qrStatus === 'confirmed' ? 'success' : qrStatus === 'expired' ? 'danger' : 'purple'" />
          <span>{{ qrExpireAt ? `有效期：${formatDateTime(qrExpireAt)}` : '尚未生成二维码' }}</span>
        </div>
        <p v-if="qrMessage" class="qr-message">{{ qrMessage }}</p>
        <div class="v2-button-row qr-actions">
          <el-button type="primary" :disabled="selectedType === 'mp_admin' && !selectedLoginProxyId" @click="createQRCode">生成二维码</el-button>
          <el-button :disabled="!qrTicket" @click="refreshQRCode">刷新二维码</el-button>
          <el-button :disabled="!qrTicket" @click="cancelQRCode">取消二维码</el-button>
        </div>
      </V2Section>

      <V2Section title="账号健康与凭证" subtitle="展示风险、冷却、fakeid、锁定代理和最近异常。">
        <el-table :data="filteredAccounts" v-loading="loading" empty-text="暂无抓取账号">
          <el-table-column prop="display_name" label="账号" min-width="160" />
          <el-table-column label="类型" width="120">
            <template #default="{ row }"><V2StatusPill :label="row.account_type === 'weread' ? '微信读书' : '公众号管理员'" tone="purple" /></template>
          </el-table-column>
          <el-table-column label="健康" width="100">
            <template #default="{ row }"><V2StatusPill :label="healthLabel(row.health_status)" :tone="row.health_status === 'normal' ? 'success' : 'warning'" /></template>
          </el-table-column>
          <el-table-column label="Fakeid" min-width="120">
            <template #default="{ row }">{{ row.metadata_json?.fakeid || (row.account_type === 'mp_admin' ? '未发现' : '-') }}</template>
          </el-table-column>
          <el-table-column label="登录代理" min-width="130">
            <template #default="{ row }">{{ row.login_proxy_id ? `#${row.login_proxy_id}` : '-' }}</template>
          </el-table-column>
          <el-table-column label="冷却至" min-width="150">
            <template #default="{ row }">{{ formatDateTime(row.cool_until) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="260" fixed="right">
            <template #default="{ row }">
              <div class="v2-button-row">
                <el-button size="small" :disabled="!canManageAccounts" @click="handleHealthCheck(row)">健康</el-button>
                <el-button v-if="row.account_type === 'mp_admin'" size="small" :disabled="!canManageAccounts" @click="handleDiscoverFakeid(row)">Fakeid</el-button>
                <el-button size="small" :disabled="!canManageAccounts" @click="prepareProxyChange(row)">代理</el-button>
                <el-button size="small" type="danger" plain :disabled="!canManageAccounts" @click="handleDelete(row)">删除</el-button>
              </div>
            </template>
          </el-table-column>
        </el-table>
      </V2Section>
    </div>

    <el-dialog v-model="proxyDialog.visible" title="更换登录代理" width="520px">
      <div class="v2-risk-note">更换登录代理会使当前凭证失效，需要重新扫码登录。</div>
      <el-select v-model="proxyDialog.login_proxy_id" filterable placeholder="选择新登录代理" style="width: 100%; margin-top: 16px">
        <el-option
          v-for="proxy in loginProxies"
          :key="proxy.id"
          :label="loginProxyLabel(proxy)"
          :value="proxy.id"
        />
      </el-select>
      <template #footer>
        <el-button @click="proxyDialog.visible = false">取消</el-button>
        <el-button type="primary" @click="saveLoginProxy">确认更换</el-button>
      </template>
    </el-dialog>
  </V2Page>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import V2MetricCard from '@/components/v2/V2MetricCard.vue'
import V2Page from '@/components/v2/V2Page.vue'
import V2Section from '@/components/v2/V2Section.vue'
import V2StatusPill from '@/components/v2/V2StatusPill.vue'
import { usePermissions } from '@/composables/usePermissions'
import {
  cancelCollectorQRLogin,
  deleteCollectorAccount,
  discoverCollectorFakeid,
  generateCollectorQRCode,
  getCollectorAccounts,
  getCollectorQRStatus,
  healthCheckCollectorAccount,
  updateCollectorLoginProxy
} from '@/api/collectorAccounts'
import { getProxies } from '@/api/proxies'
import { formatDateTime } from './helpers'

const { canManageAccounts } = usePermissions()
const loading = ref(false)
const accounts = ref([])
const filterType = ref('')
const filterHealth = ref('')
const selectedType = ref('mp_admin')
const selectedLoginProxyId = ref(null)
const loginProxies = ref([])
const qrTicket = ref('')
const qrUrl = ref('')
const qrStatus = ref('waiting')
const qrExpireAt = ref('')
const qrMessage = ref('')
const proxyDialog = reactive({ visible: false, account: null, login_proxy_id: null })
let pollTimer = null

const filteredAccounts = computed(() => accounts.value.filter(item => {
  if (filterType.value && item.account_type !== filterType.value) return false
  if (filterHealth.value && item.health_status !== filterHealth.value) return false
  return true
}))
const healthyCount = computed(() => accounts.value.filter(item => item.health_status === 'normal').length)
const expiringSoonCount = computed(() => accounts.value.filter(item => daysUntil(item.expires_at) !== null && daysUntil(item.expires_at) <= 2).length)
const failureCount = computed(() => accounts.value.filter(item => item.last_failure_at || item.last_error_category).length)

onMounted(() => {
  loadAccounts()
  loadLoginProxies()
  window.addEventListener('v2-open-collector-create', focusCreate)
})
onBeforeUnmount(() => {
  stopPolling()
  window.removeEventListener('v2-open-collector-create', focusCreate)
})

function focusCreate() {
  document.querySelector('.qr-box')?.scrollIntoView({ behavior: 'smooth', block: 'center' })
}

async function loadAccounts() {
  loading.value = true
  try {
    const response = await getCollectorAccounts()
    accounts.value = response.data?.items || []
  } finally {
    loading.value = false
  }
}

async function loadLoginProxies() {
  const response = await getProxies({ page: 1, page_size: 100, active_only: true })
  loginProxies.value = (response.data?.items || []).filter(proxy => {
    return ['isp_static', 'residential_static', 'mobile_static'].includes(proxy.proxy_kind)
  })
}

function loginProxyLabel(proxy) {
  const serviceKeys = proxy.service_keys || []
  const boundLabel = serviceKeys.includes('mp_admin_login') ? '已绑定登录' : '可绑定登录'
  return `#${proxy.id} ${proxy.host}:${proxy.port} · ${proxy.proxy_kind} · ${boundLabel}`
}

async function createQRCode() {
  try {
    const response = await generateCollectorQRCode(selectedType.value, selectedType.value === 'mp_admin' ? selectedLoginProxyId.value : undefined)
    qrTicket.value = response.data.ticket
    qrUrl.value = response.data.qr_url
    qrExpireAt.value = response.data.expire_at
    qrStatus.value = 'waiting'
    qrMessage.value = ''
    startPolling()
  } catch (error) {
    qrMessage.value = error?.response?.data?.detail || error?.response?.data?.error || '二维码生成失败'
  }
}

async function refreshQRCode() {
  if (qrTicket.value) await cancelCollectorQRLogin(qrTicket.value)
  resetQR()
  await createQRCode()
}

async function cancelQRCode() {
  if (qrTicket.value) await cancelCollectorQRLogin(qrTicket.value)
  resetQR()
}

function resetQR() {
  stopPolling()
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
  if (pollTimer) window.clearInterval(pollTimer)
  pollTimer = null
}

async function checkQRStatus() {
  if (!qrTicket.value) return
  try {
    const response = await getCollectorQRStatus(qrTicket.value)
    qrStatus.value = response.data.status
    qrMessage.value = response.data.message || ''
    if (response.data.status === 'confirmed') {
      ElMessage.success('抓取账号绑定成功')
      resetQR()
      await loadAccounts()
    }
    if (response.data.status === 'expired') stopPolling()
  } catch {
    qrMessage.value = '二维码状态查询失败'
    stopPolling()
  }
}

async function handleHealthCheck(account) {
  const response = await healthCheckCollectorAccount(account.id)
  accounts.value = accounts.value.map(item => item.id === account.id ? response.data : item)
}

async function handleDiscoverFakeid(account) {
  const response = await discoverCollectorFakeid(account.id)
  accounts.value = accounts.value.map(item => item.id === account.id ? response.data : item)
}

function prepareProxyChange(account) {
  proxyDialog.account = account
  proxyDialog.login_proxy_id = account.login_proxy_id || null
  proxyDialog.visible = true
}

async function saveLoginProxy() {
  if (!proxyDialog.account) return
  await updateCollectorLoginProxy(proxyDialog.account.id, proxyDialog.login_proxy_id)
  ElMessage.success('登录代理已更换，请重新扫码登录')
  proxyDialog.visible = false
  await loadAccounts()
}

async function handleDelete(account) {
  await ElMessageBox.confirm(`确定删除抓取账号“${account.display_name}”吗？`, '删除确认', { type: 'warning' })
  await deleteCollectorAccount(account.id)
  await loadAccounts()
}

function healthLabel(status) {
  return ({ normal: '正常', restricted: '受限', expired: '过期', invalid: '不可用' })[status] || status || '-'
}

function qrStatusLabel(status) {
  return ({ waiting: '等待扫码', scanned: '已扫码', confirmed: '登录成功', expired: '已过期' })[status] || status
}

function daysUntil(value) {
  if (!value) return null
  return Math.max(0, Math.ceil((new Date(value).getTime() - Date.now()) / 86400000))
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.capture-grid {
  display: grid;
  grid-template-columns: 430px minmax(0, 1fr);
  gap: 24px;
  margin-top: 24px;
}

.type-switch {
  display: flex;
  border-radius: 999px;
  background: $v2-card-soft;
  padding: 5px;
  margin-bottom: 18px;

  button {
    flex: 1;
    border: 0;
    border-radius: 999px;
    padding: 12px;
    background: transparent;
    font-weight: 950;
    cursor: pointer;

    &.active {
      background: $v2-purple;
      color: #fff;
    }
  }
}

.field {
  display: grid;
  gap: 8px;
  margin-bottom: 14px;

  span {
    color: $v2-muted;
    font-weight: 900;
  }
}

.qr-box {
  width: 210px;
  height: 210px;
  margin: 22px auto;
  border-radius: 28px;
  background: $v2-card-soft;
  display: grid;
  place-items: center;
  color: $v2-purple;
  font-size: 24px;
  font-weight: 950;

  img {
    width: 100%;
    height: 100%;
    object-fit: contain;
    padding: 18px;
  }
}

.qr-state-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: $v2-muted;
  font-size: 13px;
  font-weight: 800;
  margin-bottom: 12px;
}

.qr-message {
  color: $v2-orange;
  font-weight: 900;
  text-align: center;
}

.qr-actions {
  justify-content: center;
}

@media (max-width: 1100px) {
  .capture-grid {
    grid-template-columns: 1fr;
  }
}
</style>
