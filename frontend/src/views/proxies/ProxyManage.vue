<template>
  <div class="proxy-manage">
    <div class="page-header">
      <div>
        <h2>代理管理</h2>
        <p>按具体服务链路维护代理池，支持测试、停用和删除。</p>
      </div>
      <div class="header-actions">
        <el-select v-model="selectedServiceType" clearable filterable placeholder="服务类型" style="width: 180px" @change="loadData">
          <el-option v-for="type in serviceTypes" :key="type" :label="type" :value="type" />
        </el-select>
        <el-switch v-model="activeOnly" active-text="仅显示启用" @change="loadData" />
      </div>
    </div>

    <div class="stats-grid">
      <StatCard label="总代理" :value="stats.total" :icon="Connection" />
      <StatCard label="已启用" :value="stats.active" :icon="CircleCheck" />
      <StatCard label="平均成功率" :value="`${stats.averageRate}%`" :icon="TrendCharts" />
      <StatCard label="当前筛选" :value="selectedServiceType || '全部'" :icon="Monitor" />
    </div>

    <div class="content-grid">
      <div class="table-card card-static">
        <el-table :data="proxies" v-loading="loading" empty-text="暂无代理">
          <el-table-column label="地址" min-width="180">
            <template #default="{ row }">{{ row.host }}:{{ row.port }}</template>
          </el-table-column>
          <el-table-column prop="service_type" label="服务类型" width="130" />
          <el-table-column prop="username" label="用户名" width="120" />
          <el-table-column label="成功率" width="160">
            <template #default="{ row }">
              <el-progress :percentage="Math.round(row.success_rate || 0)" :stroke-width="8" />
            </template>
          </el-table-column>
          <el-table-column label="启用状态" width="120">
            <template #default="{ row }">
              <el-switch
                v-if="canManageAccounts"
                :model-value="row.is_active"
                @change="toggleProxy(row, $event)"
              />
              <el-tag v-else :type="row.is_active ? 'success' : 'info'">
                {{ row.is_active ? '启用' : '停用' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column label="更新时间" min-width="180">
            <template #default="{ row }">{{ formatDateTime(row.updated_at) }}</template>
          </el-table-column>
          <el-table-column label="操作" width="180" fixed="right">
            <template #default="{ row }">
              <div v-if="canManageAccounts" class="table-actions">
                <el-button size="small" @click="handleTest(row)">测试</el-button>
                <el-button size="small" type="danger" @click="handleDelete(row)">删除</el-button>
              </div>
              <span v-else class="muted-placeholder">只读</span>
            </template>
          </el-table-column>
      </el-table>
    </div>

      <div v-if="canManageAccounts" class="form-card card-static">
        <h3>添加代理</h3>
        <el-form :model="proxyForm" label-position="top">
          <el-form-item label="Host">
            <el-input v-model="proxyForm.host" placeholder="127.0.0.1" />
          </el-form-item>
          <el-form-item label="Port">
            <el-input-number v-model="proxyForm.port" :min="1" :max="65535" style="width: 100%" />
          </el-form-item>
          <el-form-item label="服务类型">
            <el-select v-model="proxyForm.service_type" style="width: 100%">
              <el-option v-for="type in serviceTypes" :key="type" :label="type" :value="type" />
            </el-select>
          </el-form-item>
          <el-form-item label="用户名">
            <el-input v-model="proxyForm.username" />
          </el-form-item>
          <el-form-item label="密码">
            <el-input v-model="proxyForm.password" show-password />
          </el-form-item>
          <el-button type="primary" :loading="creating" @click="handleCreate">添加代理</el-button>
        </el-form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { CircleCheck, Connection, Monitor, TrendCharts } from '@element-plus/icons-vue'
import StatCard from '@/components/common/StatCard.vue'
import { usePermissions } from '@/composables/usePermissions'
import { addProxy, checkProxy, deleteProxy, getProxies, updateProxy } from '@/api/proxies'

const serviceTypes = ['polling', 'fetch', 'parse', 'ai', 'weread_list', 'weread_detail', 'mp_list', 'mp_detail']
const { canManageAccounts } = usePermissions()
const loading = ref(false)
const creating = ref(false)
const proxies = ref([])
const selectedServiceType = ref('')
const activeOnly = ref(true)

const proxyForm = reactive({
  host: '',
  port: 8080,
  service_type: 'mp_list',
  username: '',
  password: ''
})

const stats = computed(() => {
  const total = proxies.value.length
  const active = proxies.value.filter((item) => item.is_active).length
  const averageRate = total ? Math.round(proxies.value.reduce((sum, item) => sum + (item.success_rate || 0), 0) / total) : 0
  return { total, active, averageRate }
})

onMounted(loadData)

async function loadData() {
  loading.value = true
  try {
    const response = await getProxies({
      page: 1,
      page_size: 100,
      service_type: selectedServiceType.value || undefined,
      active_only: activeOnly.value
    })
    proxies.value = response.data?.items || []
  } catch (error) {
    ElMessage.error(error?.response?.data?.detail || error?.response?.data?.error || '代理列表加载失败')
  } finally {
    loading.value = false
  }
}

async function handleCreate() {
  if (!proxyForm.host.trim()) {
    ElMessage.warning('请先输入代理 Host')
    return
  }
  creating.value = true
  try {
    await addProxy({
      host: proxyForm.host,
      port: proxyForm.port,
      service_type: proxyForm.service_type,
      username: proxyForm.username || undefined,
      password: proxyForm.password || undefined
    })
    ElMessage.success('代理添加成功')
    proxyForm.host = ''
    proxyForm.port = 8080
    proxyForm.username = ''
    proxyForm.password = ''
    await loadData()
  } finally {
    creating.value = false
  }
}

async function handleTest(proxy) {
  const response = await checkProxy(proxy.id)
  ElMessage[response.data.success ? 'success' : 'warning'](
    response.data.success ? `代理可用，延迟 ${Math.round(response.data.latency_ms || 0)}ms` : `代理测试失败：${response.data.error}`
  )
  await loadData()
}

async function toggleProxy(proxy, value) {
  await updateProxy(proxy.id, { is_active: value })
  ElMessage.success('代理状态已更新')
  await loadData()
}

async function handleDelete(proxy) {
  await ElMessageBox.confirm(`确定删除代理 ${proxy.host}:${proxy.port} 吗？`, '删除确认', { type: 'warning' })
  await deleteProxy(proxy.id)
  ElMessage.success('代理已删除')
  await loadData()
}

function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}
</script>

<style lang="scss" scoped>
.proxy-manage {
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

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 24px;
}

.table-card,
.form-card {
  padding: 20px;
}

.form-card h3 {
  margin-top: 0;
}

.muted-placeholder {
  color: $color-text-secondary;
}

@media (max-width: 900px) {
  .stats-grid,
  .content-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .table-card,
  .form-card {
    padding: 16px;
  }
}
</style>
