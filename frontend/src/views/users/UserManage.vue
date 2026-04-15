<template>
  <div class="user-manage">
    <div class="stats-row">
      <StatCard label="总用户数" :value="stats.totalUsers" :icon="User" />
      <StatCard label="WeRead 账号" :value="stats.wereadAccounts" :icon="Notebook" />
      <StatCard label="MP 账号" :value="stats.mpAccounts" :icon="Memo" />
      <StatCard label="即将到期" :value="stats.expiringSoon" :icon="Warning" icon-color="#FF3D00" icon-bg="rgba(255, 61, 0, 0.1)" />
    </div>

    <el-tabs v-model="activeTab">
      <el-tab-pane label="系统用户" name="users">
        <div class="table-container card-static">
          <el-table :data="users" v-loading="loading" stripe>
            <el-table-column prop="username" label="用户名" width="140" />
            <el-table-column prop="email" label="邮箱" min-width="180" />
            <el-table-column prop="role" label="角色" width="100">
              <template #default="{ row }">
                <el-tag :type="row.role === 'admin' ? 'danger' : 'info'" size="small">
                  {{ row.role }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="last_login" label="最后登录" width="160">
              <template #default="{ row }">
                {{ row.last_login ? formatDateTime(row.last_login) : '-' }}
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <el-tag :type="row.status === 'active' ? 'success' : 'info'" size="small">
                  {{ row.status === 'active' ? '活跃' : '停用' }}
                </el-tag>
              </template>
            </el-table-column>
            <el-table-column label="操作" width="160" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="handleEditUser(row)">
                  <el-icon><Edit /></el-icon>
                </el-button>
                <el-button size="small" type="danger" @click="handleDeleteUser(row)">
                  <el-icon><Delete /></el-icon>
                </el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>

      <el-tab-pane label="公众号账号" name="accounts">
        <div v-if="expiringAccounts.length > 0" class="expiring-warning card-static">
          <el-icon color="#FF3D00" :size="20"><Warning /></el-icon>
          <span>以下账号将在 30 天内到期：</span>
          <el-tag v-for="account in expiringAccounts" :key="account.id" type="danger" size="small">
            {{ account.name }} ({{ account.expire_date }})
          </el-tag>
        </div>

        <div class="table-container card-static">
          <el-table :data="pubAccounts" v-loading="loading" stripe>
            <el-table-column prop="name" label="名称" width="140" />
            <el-table-column prop="type" label="类型" width="100">
              <template #default="{ row }">
                <el-tag size="small">{{ row.type }}</el-tag>
              </template>
            </el-table-column>
            <el-table-column prop="biz" label="Biz" width="140">
              <template #default="{ row }">
                <span class="biz-text">{{ row.biz || '-' }}</span>
              </template>
            </el-table-column>
            <el-table-column prop="status" label="状态" width="80">
              <template #default="{ row }">
                <StatusTag :status="row.status" />
              </template>
            </el-table-column>
            <el-table-column prop="expire_date" label="到期时间" width="120" />
            <el-table-column prop="tier" label="Tier" width="80">
              <template #default="{ row }">
                <StatusTag :tier="row.tier" />
              </template>
            </el-table-column>
            <el-table-column prop="score" label="Score" width="100">
              <template #default="{ row }">
                <el-progress
                  :percentage="row.score || 0"
                  :stroke-width="6"
                  :color="getScoreColor(row.score)"
                />
              </template>
            </el-table-column>
            <el-table-column label="操作" width="100" fixed="right">
              <template #default="{ row }">
                <el-button size="small" @click="handleRenew(row)">续期</el-button>
              </template>
            </el-table-column>
          </el-table>
        </div>
      </el-tab-pane>
    </el-tabs>

    <el-button class="add-account-btn" type="primary" circle @click="showAddDialog = true">
      <el-icon :size="24"><Plus /></el-icon>
    </el-button>

    <el-dialog v-model="showAddDialog" title="添加公众号账号" width="500px">
      <el-tabs v-model="addAccountType">
        <el-tab-pane label="WeRead" name="weread" />
        <el-tab-pane label="公众号" name="mp" />
      </el-tabs>

      <div class="qr-placeholder">
        <div class="qr-box">
          <el-icon :size="64" color="#ccc"><Picture /></el-icon>
          <p>请扫描二维码添加账号</p>
        </div>
      </div>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Notebook, Memo, Warning, Edit, Delete, Plus, Picture } from '@element-plus/icons-vue'
import StatCard from '@/components/common/StatCard.vue'
import StatusTag from '@/components/common/StatusTag.vue'
import { getUsers, createUser, deleteUser } from '@/api/users'

const activeTab = ref('users')
const loading = ref(false)
const showAddDialog = ref(false)
const addAccountType = ref('weread')
const users = ref([])
const pubAccounts = ref([])
const expiringAccounts = ref([])
const stats = ref({
  totalUsers: 0,
  wereadAccounts: 0,
  mpAccounts: 0,
  expiringSoon: 0
})

onMounted(async () => {
  await fetchUsers()
  await fetchPubAccounts()
})

async function fetchUsers() {
  loading.value = true
  try {
    const response = await getUsers()
    users.value = response.data || []
    stats.value.totalUsers = users.value.length
  } catch (error) {
    console.error('Failed to fetch users:', error)
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

async function fetchPubAccounts() {
  // Mock data for demo
  pubAccounts.value = [
    { id: 1, name: '科技每日推送', type: 'WeRead', biz: 'tech_daily', status: 'active', expire_date: '2026-05-01', tier: 'S', score: 95 },
    { id: 2, name: '财经观察', type: 'MP', biz: 'finance_view', status: 'active', expire_date: '2026-04-20', tier: 'A', score: 78 },
    { id: 3, name: '生活小技巧', type: 'WeRead', biz: 'life_tips', status: 'inactive', expire_date: '2026-06-15', tier: 'B', score: 62 }
  ]

  const thirtyDaysFromNow = new Date()
  thirtyDaysFromNow.setDate(thirtyDaysFromNow.getDate() + 30)

  expiringAccounts.value = pubAccounts.value.filter(a => {
    const expireDate = new Date(a.expire_date)
    return expireDate <= thirtyDaysFromNow && expireDate > new Date()
  })

  stats.value.expiringSoon = expiringAccounts.value.length
  stats.value.wereadAccounts = pubAccounts.value.filter(a => a.type === 'WeRead').length
  stats.value.mpAccounts = pubAccounts.value.filter(a => a.type === 'MP').length
}

async function handleEditUser(user) {
  // Open edit dialog
}

async function handleDeleteUser(user) {
  try {
    await ElMessageBox.confirm('确定删除该用户吗？', '警告', { type: 'warning' })
    await deleteUser(user.id)
    ElMessage.success('删除成功')
    fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      ElMessage.error('删除失败')
    }
  }
}

async function handleRenew(account) {
  ElMessage.success('续期成功')
}

function formatDateTime(date) {
  return new Date(date).toLocaleString('zh-CN')
}

function getScoreColor(score) {
  if (score >= 80) return '#22C55E'
  if (score >= 60) return '#FF6B00'
  return '#FF3D00'
}
</script>

<style lang="scss" scoped>
.user-manage {
  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    margin-bottom: 24px;
  }

  .table-container {
    padding: 20px;
  }

  .biz-text {
    font-family: monospace;
    font-size: 13px;
  }

  .expiring-warning {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 16px;
    margin-bottom: 20px;
    background: rgba(#FF3D00, 0.05);
    border: 1px solid rgba(#FF3D00, 0.2);

    span {
      font-weight: 500;
    }
  }

  .add-account-btn {
    position: fixed;
    right: 40px;
    bottom: 40px;
    width: 56px;
    height: 56px;
    box-shadow: 0 4px 20px rgba($color-primary, 0.4);
  }

  .qr-placeholder {
    display: flex;
    justify-content: center;
    padding: 40px;
  }

  .qr-box {
    text-align: center;

    p {
      margin-top: 16px;
      color: $color-text-secondary;
    }
  }
}
</style>
