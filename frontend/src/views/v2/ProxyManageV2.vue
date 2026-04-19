<template>
  <V2Page
    title="代理管理"
    subtitle="代理只在手动绑定服务后使用；账号登录/列表代理请在抓取账号页绑定。"
    watermark="PROXY"
    action-rail="代理功能：新增代理 / 批量导入 / 测试代理 / 编辑详情服务绑定 / 冷却与恢复 / 删除影响提示"
  >
    <template #header-actions>
      <div class="v2-page-actions">
        <el-select v-model="selectedServiceKey" clearable placeholder="服务" style="width: 190px" @change="loadData">
          <el-option v-for="service in services" :key="service.key" :label="service.label" :value="service.key" />
        </el-select>
        <el-button @click="showCreate = true">新增代理</el-button>
        <el-button type="warning" @click="showBulk = true">批量导入</el-button>
      </div>
    </template>

    <div class="v2-grid v2-grid-4">
      <V2MetricCard label="代理总数" :value="stats.total || 0" />
      <V2MetricCard label="启用" :value="stats.active || 0" />
      <V2MetricCard label="冷却中" :value="stats.cooling || 0" warm />
      <V2MetricCard label="平均成功率" :value="`${Math.round(stats.average_success_rate || 0)}%`" />
    </div>

    <V2Section title="代理与服务绑定" subtitle="展开行可以编辑服务绑定；不兼容服务必须说明原因。">
      <el-table :data="proxies" v-loading="loading" row-key="id" empty-text="暂无代理" @expand-change="handleExpandChange">
        <el-table-column label="代理" min-width="190">
          <template #default="{ row }"><strong>#{{ row.id }} {{ row.host }}:{{ row.port }}</strong></template>
        </el-table-column>
        <el-table-column label="类型" width="150">
          <template #default="{ row }">{{ proxyKindLabel(row.proxy_kind) }}</template>
        </el-table-column>
        <el-table-column label="轮换" width="130">
          <template #default="{ row }">{{ row.rotation_mode || '-' }}</template>
        </el-table-column>
        <el-table-column label="成功率" width="100">
          <template #default="{ row }">{{ Math.round(row.success_rate || 0) }}%</template>
        </el-table-column>
        <el-table-column label="冷却" min-width="150">
          <template #default="{ row }">{{ formatDateTime(row.fail_until) }}</template>
        </el-table-column>
        <el-table-column label="状态" width="110">
          <template #default="{ row }"><V2StatusPill :label="row.is_active ? '启用' : '停用'" :tone="row.is_active ? 'success' : 'warning'" /></template>
        </el-table-column>
        <el-table-column type="expand" width="92">
          <template #default="{ row }">
            <div class="proxy-expand">
              <h4>服务绑定</h4>
              <div class="service-editor">
                <el-checkbox-group
                  class="service-checkboxes"
                  :model-value="serviceDrafts[row.id] || row.service_keys || []"
                  @change="value => setServiceDraft(row, value)"
                >
                  <el-checkbox
                    v-for="service in services"
                    :key="service.key"
                    :label="service.key"
                    :disabled="Boolean(incompatibleReason(row, service))"
                  >
                    {{ service.label }}
                  </el-checkbox>
                </el-checkbox-group>
                <div class="expand-actions">
                  <el-button type="primary" :loading="serviceSaving[row.id]" @click="saveProxyServices(row)">保存绑定</el-button>
                  <el-button @click="handleTest(row)">测试代理</el-button>
                  <el-button @click="toggleProxy(row, !row.is_active)">{{ row.is_active ? '停用代理' : '启用代理' }}</el-button>
                  <el-button type="danger" plain @click="handleDelete(row)">删除代理</el-button>
                </div>
              </div>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </V2Section>

    <el-dialog v-model="showCreate" title="新增代理" width="720px">
      <el-form :model="form" label-position="top">
        <div class="form-grid">
          <el-form-item label="Host"><el-input v-model="form.host" /></el-form-item>
          <el-form-item label="Port"><el-input-number v-model="form.port" :min="1" :max="65535" style="width: 100%" /></el-form-item>
          <el-form-item label="用户名"><el-input v-model="form.username" /></el-form-item>
          <el-form-item label="密码"><el-input v-model="form.password" show-password /></el-form-item>
          <el-form-item label="代理类型"><el-select v-model="form.proxy_kind"><el-option v-for="kind in proxyKinds" :key="kind" :label="proxyKindLabel(kind)" :value="kind" /></el-select></el-form-item>
          <el-form-item label="轮换模式">
            <el-select v-model="form.rotation_mode">
              <el-option v-for="mode in rotationModes" :key="mode.value" :label="mode.label" :value="mode.value" />
            </el-select>
          </el-form-item>
          <el-form-item label="粘性时长"><el-input-number v-model="form.sticky_ttl_seconds" :min="0" style="width: 100%" /></el-form-item>
          <el-form-item label="供应商"><el-input v-model="form.provider_name" /></el-form-item>
        </div>
        <el-form-item label="绑定服务">
          <el-checkbox-group v-model="form.service_keys">
            <el-checkbox v-for="service in compatibleServices(form)" :key="service.key" :label="service.key">{{ service.label }}</el-checkbox>
          </el-checkbox-group>
        </el-form-item>
        <el-form-item label="备注"><el-input v-model="form.notes" type="textarea" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showCreate = false">取消</el-button>
        <el-button type="primary" :loading="creating" @click="handleCreate">添加</el-button>
      </template>
    </el-dialog>

    <el-dialog v-model="showBulk" title="批量导入代理" width="720px">
      <el-input v-model="bulkText" type="textarea" :rows="8" placeholder="host:port:user:pass，每行一个" />
      <div class="v2-risk-note" style="margin-top: 14px">批量导入会使用当前选择的代理类型和服务绑定。</div>
      <el-form label-position="top" style="margin-top: 16px">
        <el-form-item label="代理类型"><el-select v-model="bulkKind"><el-option v-for="kind in proxyKinds" :key="kind" :label="proxyKindLabel(kind)" :value="kind" /></el-select></el-form-item>
        <el-form-item label="绑定服务"><el-checkbox-group v-model="bulkServices"><el-checkbox v-for="service in compatibleServices({ proxy_kind: bulkKind, sticky_ttl_seconds: 0 })" :key="service.key" :label="service.key">{{ service.label }}</el-checkbox></el-checkbox-group></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showBulk = false">取消</el-button>
        <el-button type="primary" :loading="bulkCreating" @click="handleBulkCreate">导入</el-button>
      </template>
    </el-dialog>
  </V2Page>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import V2MetricCard from '@/components/v2/V2MetricCard.vue'
import V2Page from '@/components/v2/V2Page.vue'
import V2Section from '@/components/v2/V2Section.vue'
import V2StatusPill from '@/components/v2/V2StatusPill.vue'
import { addProxy, bulkAddProxies, checkProxy, deleteProxy, getProxies, getProxyStats, updateProxy, updateProxyServices } from '@/api/proxies'
import { formatDateTime } from './helpers'

const services = [
  { key: 'mp_detail', label: '公众号详情' },
  { key: 'weread_detail', label: 'WeRead 详情' },
  { key: 'image_proxy', label: '图片代理' },
  { key: 'ai', label: 'AI 请求' }
]
const proxyKinds = ['isp_static', 'residential_static', 'residential_rotating', 'mobile_rotating', 'custom_gateway', 'mobile_static', 'datacenter']
const loading = ref(false)
const creating = ref(false)
const bulkCreating = ref(false)
const proxies = ref([])
const stats = ref({})
const selectedServiceKey = ref('')
const showCreate = ref(false)
const showBulk = ref(false)
const bulkText = ref('')
const bulkKind = ref('residential_rotating')
const bulkServices = ref([])
const serviceDrafts = ref({})
const serviceSaving = ref({})
const rotationModes = [
  { label: '固定', value: 'fixed' },
  { label: '粘性', value: 'sticky' },
  { label: '轮询', value: 'round_robin' },
  { label: '每次请求', value: 'per_request' },
  { label: '服务商自动', value: 'provider_auto' }
]
const form = reactive({ host: '', port: 8080, username: '', password: '', proxy_kind: 'residential_static', rotation_mode: 'fixed', sticky_ttl_seconds: 0, provider_name: '', notes: '', service_keys: [] })
const openBulkDialog = () => { showBulk.value = true }

onMounted(() => {
  loadData()
  window.addEventListener('v2-open-proxy-bulk', openBulkDialog)
})
onUnmounted(() => window.removeEventListener('v2-open-proxy-bulk', openBulkDialog))

async function loadData() {
  loading.value = true
  try {
    const [list, stat] = await Promise.all([
      getProxies({ page: 1, page_size: 100, active_only: false, service_key: selectedServiceKey.value || undefined }),
      getProxyStats()
    ])
    proxies.value = list.data?.items || []
    stats.value = stat.data || {}
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  creating.value = true
  try {
    await addProxy(proxyPayload(form))
    showCreate.value = false
    await loadData()
  } finally {
    creating.value = false
  }
}

async function handleBulkCreate() {
  const items = bulkText.value.split('\n').map(line => line.trim()).filter(Boolean).map(line => {
    const [host, port, username, password] = line.split(':')
    return proxyPayload({
      host,
      port: Number(port),
      username,
      password,
      proxy_kind: bulkKind.value,
      rotation_mode: bulkKind.value.includes('rotating') ? 'round_robin' : 'fixed',
      sticky_ttl_seconds: 0,
      service_keys: bulkServices.value
    })
  })
  if (!items.length) return
  bulkCreating.value = true
  try {
    await bulkAddProxies({ proxies: items })
    showBulk.value = false
    bulkText.value = ''
    await loadData()
  } finally {
    bulkCreating.value = false
  }
}

function handleExpandChange(proxy, expandedRows) {
  if (expandedRows.some(item => item.id === proxy.id) && !serviceDrafts.value[proxy.id]) {
    serviceDrafts.value = { ...serviceDrafts.value, [proxy.id]: [...(proxy.service_keys || [])] }
  }
}

function setServiceDraft(proxy, value) {
  serviceDrafts.value = { ...serviceDrafts.value, [proxy.id]: value }
}

async function saveProxyServices(proxy) {
  serviceSaving.value = { ...serviceSaving.value, [proxy.id]: true }
  try {
    await updateProxyServices(proxy.id, { service_keys: serviceDrafts.value[proxy.id] || [] })
    await loadData()
  } finally {
    serviceSaving.value = { ...serviceSaving.value, [proxy.id]: false }
  }
}

async function handleTest(proxy) {
  const response = await checkProxy(proxy.id)
  ElMessage[response.data?.success ? 'success' : 'warning'](response.data?.success ? '代理测试通过' : (response.data?.error || '代理测试未通过'))
  await loadData()
}

async function toggleProxy(proxy, value) {
  await updateProxy(proxy.id, { ...proxy, is_active: value })
  await loadData()
}

async function handleDelete(proxy) {
  await ElMessageBox.confirm(`删除代理 ${proxy.host}:${proxy.port} 后，已绑定账号会恢复直连。确认删除？`, '删除影响提示', { type: 'warning' })
  await deleteProxy(proxy.id)
  await loadData()
}

function compatibleServices(proxy) {
  return services.filter(service => !incompatibleReason(proxy, service))
}

function incompatibleReason(proxy, service) {
  const kind = proxy.proxy_kind
  if (kind === 'datacenter' && service.key !== 'ai') return '数据中心代理不用于微信链路'
  if (['residential_rotating', 'mobile_rotating', 'custom_gateway'].includes(kind)) {
    if (service.key === 'ai') return 'AI 请求建议使用数据中心或静态代理'
  }
  if (['isp_static', 'residential_static', 'mobile_static'].includes(kind) && ['image_proxy', 'ai'].includes(service.key)) return ''
  return ''
}

function serviceLabel(key) {
  return services.find(item => item.key === key)?.label || key
}

function proxyKindLabel(kind) {
  return ({ isp_static: '静态 ISP', residential_static: '静态住宅', residential_rotating: '旋转住宅', mobile_rotating: '旋转移动', custom_gateway: '短效网关', mobile_static: '静态移动', datacenter: '数据中心' })[kind] || kind
}

function proxyPayload(source) {
  const payload = { ...source }
  if (!payload.username) payload.username = null
  if (!payload.password) payload.password = null
  if (!payload.provider_name) payload.provider_name = null
  if (!payload.notes) payload.notes = null
  payload.sticky_ttl_seconds = Number(payload.sticky_ttl_seconds) > 0 ? Number(payload.sticky_ttl_seconds) : null
  return payload
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.proxy-expand {
  padding: 18px clamp(16px, 4vw, 44px);
  max-width: 100%;
  overflow: hidden;

  h4 {
    margin: 0 0 12px;
  }
}

.service-editor {
  margin-top: 16px;
  display: grid;
  gap: 14px;
}

.service-checkboxes {
  :deep(.el-checkbox-group) {
    width: 100%;
  }
}

:deep(.service-checkboxes.el-checkbox-group) {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(138px, 1fr));
  gap: 12px 18px;
  align-items: center;
}

:deep(.service-checkboxes .el-checkbox) {
  margin-right: 0;
  min-width: 0;
}

.expand-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
  align-items: center;

  .el-button {
    margin-left: 0;
  }
}

.form-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

:deep(.el-table__expand-icon) {
  width: 64px;
  height: 30px;
  transform: none !important;
  border-radius: 999px;
  background: #fff;
  box-shadow: 0 0 0 1px rgba($v2-line, 0.8) inset;
  color: $v2-ink;
  font-size: 12px;
  font-weight: 950;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  white-space: nowrap;
}

:deep(.el-table__expand-icon .el-icon) {
  display: none;
}

:deep(.el-table__expand-icon::before) {
  content: '展开';
}

:deep(.el-table__expand-icon--expanded::before) {
  content: '收起';
}
</style>
