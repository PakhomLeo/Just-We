<template>
  <div class="account-list">
    <div class="toolbar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索账号名称"
        :prefix-icon="Search"
        style="width: 240px"
        clearable
      />

      <el-select v-model="tierFilter" placeholder="Tier" clearable style="width: 120px">
        <el-option label="S" value="S" />
        <el-option label="A" value="A" />
        <el-option label="B" value="B" />
        <el-option label="C" value="C" />
      </el-select>

      <el-select v-model="statusFilter" placeholder="状态" clearable style="width: 120px">
        <el-option label="活跃" value="active" />
        <el-option label="停用" value="inactive" />
      </el-select>

      <el-button type="primary" @click="showAddDialog = true">
        <el-icon><Plus /></el-icon>
        添加账号
      </el-button>
    </div>

    <div class="table-container card-static">
      <el-table
        :data="filteredAccounts"
        v-loading="loading"
        @row-click="handleRowClick"
        stripe
      >
        <el-table-column prop="name" label="名称" min-width="120" />

        <el-table-column prop="biz" label="Biz" min-width="140">
          <template #default="{ row }">
            <span class="biz-text">{{ row.biz || '-' }}</span>
          </template>
        </el-table-column>

        <el-table-column prop="tier" label="Tier" width="80">
          <template #default="{ row }">
            <StatusTag :tier="row.tier" />
          </template>
        </el-table-column>

        <el-table-column prop="score" label="Score" width="180">
          <template #default="{ row }">
            <el-progress
              :percentage="row.score || 0"
              :stroke-width="8"
              :color="getScoreColor(row.score)"
            />
          </template>
        </el-table-column>

        <el-table-column prop="last_crawl" label="最后抓取" width="120">
          <template #default="{ row }">
            {{ row.last_crawl ? formatDate(row.last_crawl) : '-' }}
          </template>
        </el-table-column>

        <el-table-column prop="next_crawl" label="下次间隔" width="100">
          <template #default="{ row }">
            {{ row.next_interval ? `${row.next_interval}min` : '-' }}
          </template>
        </el-table-column>

        <el-table-column prop="status" label="状态" width="80">
          <template #default="{ row }">
            <StatusTag :status="row.status" />
          </template>
        </el-table-column>

        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click.stop="handleCrawl(row)">
              <el-icon><Refresh /></el-icon>
            </el-button>
            <el-button size="small" @click.stop="handleEdit(row)">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button size="small" type="danger" @click.stop="handleDelete(row)">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <AccountDetail
      v-model="showDetail"
      :account="selectedAccount"
      @close="showDetail = false"
    />

    <AccountForm
      v-model="showFormDialog"
      :account="editingAccount"
      @close="handleFormClose"
    />
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Search, Plus, Refresh, Edit, Delete } from '@element-plus/icons-vue'
import StatusTag from '@/components/common/StatusTag.vue'
import EmptyState from '@/components/common/EmptyState.vue'
import AccountDetail from './AccountDetail.vue'
import AccountForm from './AccountForm.vue'
import { useAccountsStore } from '@/stores/accounts'
import { getAccounts, deleteAccount, triggerCrawl } from '@/api/accounts'

const accountsStore = useAccountsStore()

const searchQuery = ref('')
const tierFilter = ref('')
const statusFilter = ref('')
const loading = ref(false)
const showDetail = ref(false)
const showFormDialog = ref(false)
const selectedAccount = ref(null)
const editingAccount = ref(null)

const filteredAccounts = computed(() => {
  return accountsStore.accounts.filter(account => {
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      if (!account.name.toLowerCase().includes(query)) return false
    }
    if (tierFilter.value && account.tier !== tierFilter.value) return false
    if (statusFilter.value && account.status !== statusFilter.value) return false
    return true
  })
})

onMounted(async () => {
  loading.value = true
  try {
    await accountsStore.fetchAccounts()
  } finally {
    loading.value = false
  }
})

function handleRowClick(row) {
  selectedAccount.value = row
  showDetail.value = true
}

function handleEdit(row) {
  editingAccount.value = row
  showFormDialog.value = true
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除该账号吗？', '警告', {
      type: 'warning'
    })
    await deleteAccount(row.id)
    ElMessage.success('删除成功')
    accountsStore.fetchAccounts()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function handleCrawl(row) {
  try {
    await triggerCrawl(row.id)
    ElMessage.success('抓取任务已启动')
  } catch (error) {
    ElMessage.error('启动抓取失败')
  }
}

function handleFormClose() {
  showFormDialog.value = false
  editingAccount.value = null
  accountsStore.fetchAccounts()
}

function formatDate(date) {
  return new Date(date).toLocaleDateString('zh-CN')
}

function getScoreColor(score) {
  if (score >= 80) return '#22C55E'
  if (score >= 60) return '#FF6B00'
  return '#FF3D00'
}
</script>

<style lang="scss" scoped>
.account-list {
  .toolbar {
    display: flex;
    gap: 12px;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }

  .table-container {
    padding: 20px;
  }

  .biz-text {
    font-family: monospace;
    font-size: 13px;
  }
}
</style>
