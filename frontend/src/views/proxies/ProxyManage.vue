<template>
  <div class="proxy-manage">
    <el-tabs v-model="activeTab" @tab-change="handleTabChange">
      <el-tab-pane label="Polling" name="polling" />
      <el-tab-pane label="Fetch" name="fetch" />
      <el-tab-pane label="Parse" name="parse" />
      <el-tab-pane label="AI" name="ai" />
    </el-tabs>

    <div class="stats-row">
      <StatCard
        label="总代理数"
        :value="stats.total"
        :icon="Connection"
      />
      <StatCard
        label="可用率"
        :value="stats.availableRate"
        :icon="CircleCheck"
        icon-color="#22C55E"
        icon-bg="rgba(34, 197, 94, 0.1)"
      />
      <StatCard
        label="最后检查"
        :value="stats.lastCheck"
        :icon="Clock"
      />
    </div>

    <div class="main-content">
      <div class="table-section">
        <div class="table-container card-static">
          <el-table :data="proxies" v-loading="loading" stripe>
            <el-table-column prop="ip" label="IP:Port" min-width="160">
              <template #default="{ row }">
                <span class="proxy-address">{{ row.ip }}:{{ row.port }}</span>
              </template>
            </el-table-column>

            <el-table-column prop="type" label="类型" width="100" />

            <el-table-column prop="success_rate" label="成功率" width="120">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.success_rate || 0"
                  :stroke-width="6"
                  :color="getRateColor(row.success_rate)"
                />
              </template>
            </el-table-column>

            <el-table-column prop="last_check" label="最后检查" width="140">
              <template #default="{ row }">
                {{ row.last_check ? formatDateTime(row.last_check) : '-' }}
              </template>
            </el-table-column>

            <el-table-column prop="status" label="状态" width="100">
              <template #default="{ row }">
                <StatusTag :status="row.status" />
              </template>
            </el-table-column>

            <el-table-column label="操作" width="120" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="handleCheck(row)">
                  <el-icon><Refresh /></el-icon>
                </el-button>
                <el-button size="small" type="danger" @click="handleDelete(row)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </div>

      <div class="add-proxy-section">
        <div class="add-proxy-card card-static">
          <h4>添加代理</h4>
          <el-form :model="proxyForm" label-position="top">
            <el-form-item label="代理地址">
              <el-input v-model="proxyForm.ip" placeholder="IP:Port" />
            </el-form-item>
            <el-form-item label="类型">
              <el-select v-model="proxyForm.type" placeholder="选择类型">
                <el-option label="HTTP" value="http" />
                <el-option label="HTTPS" value="https" />
                <el-option label="SOCKS5" value="socks5" />
              </el-select>
            </el-form-item>
            <el-button type="primary" style="width: 100%" @click="handleAdd">
              添加
            </el-button>
          </el-form>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, reactive, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Connection, CircleCheck, Clock, Refresh, Delete } from '@element-plus/icons-vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { getProxies, getProxyStats, addProxy, deleteProxy, checkProxy } from '@/api/proxies'

const activeTab = ref('polling')
const loading = ref(false)
const proxies = ref([])
const stats = ref({
  total: 0,
  availableRate: 0,
  lastCheck: '-'
})

const proxyForm = reactive({
  ip: '',
  type: 'http'
})

onMounted(async () => {
  await fetchData()
})

async function fetchData() {
  loading.value = true
  try {
    const [proxiesRes, statsRes] = await Promise.all([
      getProxies({ service_type: activeTab.value }),
      getProxyStats()
    ])
    proxies.value = proxiesRes.data?.items || []
    stats.value = statsRes.data || { total: 0, availableRate: 0, lastCheck: '-' }
  } catch (error) {
    // Silent fail
  } finally {
    loading.value = false
  }
}

function handleTabChange() {
  fetchData()
}

async function handleAdd() {
  try {
    const [host, port] = proxyForm.ip.split(':')
    await addProxy({ host, port: parseInt(port), service_type: activeTab.value })
    ElMessage.success('添加成功')
    proxyForm.ip = ''
    proxyForm.type = 'http'
    fetchData()
  } catch (error) {
    ElMessage.error('添加失败')
  }
}

async function handleDelete(row) {
  try {
    await deleteProxy(row.id)
    ElMessage.success('删除成功')
    fetchData()
  } catch (error) {
    ElMessage.error('删除失败')
  }
}

async function handleCheck(row) {
  try {
    await checkProxy(row.id)
    ElMessage.success('检查完成')
    fetchData()
  } catch (error) {
    ElMessage.error('检查失败')
  }
}

function formatDateTime(date) {
  return new Date(date).toLocaleString('zh-CN')
}

function getRateColor(rate) {
  if (rate >= 80) return '#22C55E'
  if (rate >= 50) return '#FF6B00'
  return '#FF3D00'
}
</script>

<style lang="scss" scoped>
.proxy-manage {
  .stats-row {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 20px;
    margin-bottom: 24px;
  }

  .main-content {
    display: grid;
    grid-template-columns: 1fr 280px;
    gap: 24px;
  }

  .table-container {
    padding: 20px;
  }

  .proxy-address {
    font-family: monospace;
    font-size: 13px;
  }

  .add-proxy-card {
    padding: 20px;
    position: sticky;
    top: 20px;

    h4 {
      font-size: 16px;
      font-weight: 600;
      margin-bottom: 16px;
    }
  }
}
</style>
