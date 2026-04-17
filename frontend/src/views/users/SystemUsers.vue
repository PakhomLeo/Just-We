<template>
  <div class="system-users">
    <div class="page-header">
      <h2>用户管理</h2>
      <div class="header-actions">
        <el-button type="primary" @click="handleCreate">
          <el-icon><Plus /></el-icon>
          添加用户
        </el-button>
      </div>
    </div>

    <div class="stats-row">
      <StatCard label="总用户数" :value="stats.total" :icon="User" />
      <StatCard label="管理员" :value="stats.adminCount" :icon="UserFilled" icon-color="#EF4444" icon-bg="rgba(239, 68, 68, 0.1)" />
      <StatCard label="运营者" :value="stats.operatorCount" :icon="Edit" icon-color="#F59E0B" icon-bg="rgba(245, 158, 11, 0.1)" />
      <StatCard label="查看者" :value="stats.viewerCount" :icon="View" icon-color="#6366F1" icon-bg="rgba(99, 102, 241, 0.1)" />
    </div>

    <div class="users-table card-static">
      <el-table :data="users" v-loading="loading" stripe>
        <el-table-column prop="email" label="邮箱" min-width="200" />
        <el-table-column prop="role" label="角色" width="120">
          <template #default="{ row }">
            <el-tag :type="getRoleTagType(row.role)" size="small">
              {{ getRoleName(row.role) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_active" label="状态" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_active ? 'success' : 'danger'" size="small">
              {{ row.is_active ? '活跃' : '禁用' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="is_superuser" label="超级用户" width="100">
          <template #default="{ row }">
            <el-tag :type="row.is_superuser ? 'warning' : 'info'" size="small">
              {{ row.is_superuser ? '是' : '否' }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="last_login" label="最后登录" width="180">
          <template #default="{ row }">
            {{ row.last_login ? formatDateTime(row.last_login) : '从未登录' }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="180" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="handleEdit(row)">
              <el-icon><Edit /></el-icon>
            </el-button>
            <el-button size="small" type="danger" @click="handleDelete(row)" :disabled="row.id === currentUserId">
              <el-icon><Delete /></el-icon>
            </el-button>
          </template>
        </el-table-column>
      </el-table>
    </div>

    <el-empty v-if="users.length === 0 && !loading" description="暂无用户" />

    <!-- 添加/编辑用户对话框 -->
    <el-dialog v-model="showAddDialog" :title="editingUser ? '编辑用户' : '添加用户'" width="450px" @closed="resetForm">
      <el-form :model="userForm" label-position="top" :rules="userRules" ref="userFormRef">
        <el-form-item label="邮箱" prop="email">
          <el-input v-model="userForm.email" placeholder="输入邮箱地址" :disabled="!!editingUser" />
        </el-form-item>
        <el-form-item v-if="!editingUser" label="密码" prop="password">
          <el-input v-model="userForm.password" type="password" placeholder="输入密码（至少8位）" show-password />
        </el-form-item>
        <el-form-item label="角色" prop="role">
          <el-select v-model="userForm.role" placeholder="选择角色" style="width: 100%">
            <el-option label="管理员 (admin)" value="admin" />
            <el-option label="运营者 (operator)" value="operator" />
            <el-option label="查看者 (viewer)" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="状态">
          <el-switch v-model="userForm.is_active" active-text="启用" inactive-text="禁用" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="handleCancel">取消</el-button>
        <el-button type="primary" @click="handleSave">保存</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Plus, Edit, Delete, User, UserFilled, View } from '@element-plus/icons-vue'
import StatCard from '@/components/common/StatCard.vue'
import { getUsers, createUser, updateUser, deleteUser } from '@/api/users'
import { useAuthStore } from '@/stores/auth'

const authStore = useAuthStore()
const loading = ref(false)
const showAddDialog = ref(false)
const editingUser = ref(null)
const userFormRef = ref(null)
const users = ref([])

const userForm = reactive({
  email: '',
  password: '',
  role: 'viewer',
  is_active: true
})

const userRules = {
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效的邮箱地址', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 8, message: '密码至少8位', trigger: 'blur' }
  ],
  role: [
    { required: true, message: '请选择角色', trigger: 'change' }
  ]
}

const currentUserId = computed(() => authStore.user?.id)

const stats = computed(() => ({
  total: users.value.length,
  adminCount: users.value.filter(u => u.role === 'admin').length,
  operatorCount: users.value.filter(u => u.role === 'operator').length,
  viewerCount: users.value.filter(u => u.role === 'viewer').length
}))

onMounted(async () => {
  await fetchUsers()
})

async function fetchUsers() {
  loading.value = true
  try {
    const response = await getUsers()
    users.value = response.data || []
  } catch (error) {
    console.error('Failed to fetch users:', error)
    ElMessage.error('获取用户列表失败')
  } finally {
    loading.value = false
  }
}

function handleEdit(user) {
  editingUser.value = user
  userForm.email = user.email
  userForm.password = ''
  userForm.role = user.role
  userForm.is_active = user.is_active
  showAddDialog.value = true
}

function handleCreate() {
  resetForm()
  showAddDialog.value = true
}

function handleCancel() {
  showAddDialog.value = false
}

async function handleSave() {
  try {
    await userFormRef.value.validate()

    const data = {
      email: userForm.email,
      role: userForm.role,
      is_active: userForm.is_active
    }

    if (!editingUser.value) {
      data.password = userForm.password
      await createUser(data)
      ElMessage.success('用户创建成功')
    } else {
      await updateUser(editingUser.value.id, data)
      ElMessage.success('用户更新成功')
    }

    showAddDialog.value = false
    resetForm()
    await fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to save user:', error)
      ElMessage.error('保存失败')
    }
  }
}

async function handleDelete(user) {
  try {
    await ElMessageBox.confirm('确定删除用户 "' + user.email + '" 吗？', '警告', { type: 'warning' })
    await deleteUser(user.id)
    ElMessage.success('删除成功')
    await fetchUsers()
  } catch (error) {
    if (error !== 'cancel') {
      console.error('Failed to delete user:', error)
      ElMessage.error('删除失败')
    }
  }
}

function resetForm() {
  userForm.email = ''
  userForm.password = ''
  userForm.role = 'viewer'
  userForm.is_active = true
  editingUser.value = null
}

function getRoleTagType(role) {
  const types = {
    admin: 'danger',
    operator: 'warning',
    viewer: 'info'
  }
  return types[role] || 'info'
}

function getRoleName(role) {
  const names = {
    admin: '管理员',
    operator: '运营者',
    viewer: '查看者'
  }
  return names[role] || role
}

function formatDateTime(dateStr) {
  if (!dateStr) return '-'
  const date = new Date(dateStr)
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })
}
</script>

<style lang="scss" scoped>
.system-users {
  .stats-row {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 20px;
    margin-bottom: 24px;
  }

  .users-table {
    padding: 20px;
    background: #FFFFFF;
    border-radius: 12px;
    border: 1px solid rgba(0, 0, 0, 0.05);
  }
}

@media (max-width: 900px) {
  .system-users {
    .stats-row {
      grid-template-columns: repeat(2, 1fr);
    }
  }
}

@media (max-width: 640px) {
  .system-users {
    .stats-row {
      grid-template-columns: 1fr;
    }
  }
}
</style>
