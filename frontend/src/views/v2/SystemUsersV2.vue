<template>
  <V2Page
    title="系统用户"
    subtitle="管理员创建和维护用户；角色能力必须清楚，危险操作需要 inline 风险说明。"
    watermark="USERS"
    action-rail="用户功能：新建用户 / 编辑角色 / 启用禁用 / 重置密码 / 删除用户 / 查看操作审计 / 非管理员限制"
  >
    <template #header-actions>
      <div class="v2-page-actions">
        <el-button type="warning" :disabled="!canManageUsers" @click="openCreate">新建用户</el-button>
        <el-button @click="fetchUsers">刷新</el-button>
      </div>
    </template>

    <V2Section title="用户与权限" subtitle="公开注册不作为普通入口，用户由管理员创建。">
      <div class="role-permission-list">
        <div><strong>管理员</strong><span>可管理系统设置、用户、全局策略、代理、抓取账号和全部监测数据。</span></div>
        <div><strong>操作员</strong><span>可维护监测对象、抓取流程、文章和导出任务，不能修改系统级配置和用户权限。</span></div>
        <div><strong>只读用户</strong><span>只能查看已授权范围内的仪表盘、监测对象、文章、日志和导出结果。</span></div>
      </div>
      <el-table :data="users" v-loading="loading" empty-text="暂无用户" style="margin-top: 18px">
        <el-table-column prop="email" label="邮箱" min-width="220" />
        <el-table-column label="角色" width="130"><template #default="{ row }"><V2StatusPill :label="roleLabel(row.role)" :tone="row.role === 'admin' ? 'danger' : row.role === 'operator' ? 'purple' : 'neutral'" /></template></el-table-column>
        <el-table-column label="状态" width="110"><template #default="{ row }"><V2StatusPill :label="row.is_active === false ? '禁用' : '启用'" :tone="row.is_active === false ? 'warning' : 'success'" /></template></el-table-column>
        <el-table-column label="最近登录" min-width="160"><template #default="{ row }">{{ formatDateTime(row.last_login || row.last_login_at) }}</template></el-table-column>
        <el-table-column label="创建时间" min-width="160"><template #default="{ row }">{{ formatDateTime(row.created_at) }}</template></el-table-column>
        <el-table-column label="操作" width="260" fixed="right">
          <template #default="{ row }">
            <div class="v2-button-row">
              <el-button size="small" :disabled="!canManageUsers" @click="openEdit(row)">编辑</el-button>
              <el-button size="small" :disabled="!canManageUsers" @click="toggleUser(row)">{{ row.is_active === false ? '启用' : '禁用' }}</el-button>
              <el-button size="small" type="danger" plain :disabled="!canManageUsers" @click="handleDelete(row)">删除</el-button>
            </div>
          </template>
        </el-table-column>
      </el-table>
    </V2Section>

    <el-dialog v-model="dialog.visible" :title="dialog.editing ? '编辑用户' : '创建用户'" width="520px">
      <el-form :model="form" label-position="top">
        <el-form-item label="邮箱"><el-input v-model="form.email" /></el-form-item>
        <el-form-item v-if="!dialog.editing" label="密码"><el-input v-model="form.password" show-password /></el-form-item>
        <el-form-item label="角色">
          <el-select v-model="form.role" style="width: 100%">
            <el-option label="管理员" value="admin" />
            <el-option label="操作员" value="operator" />
            <el-option label="只读用户" value="viewer" />
          </el-select>
        </el-form-item>
        <el-form-item label="启用"><el-switch v-model="form.is_active" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialog.visible = false">取消</el-button>
        <el-button type="primary" :loading="saving" @click="saveUser">保存</el-button>
      </template>
    </el-dialog>
  </V2Page>
</template>

<script setup>
import { onMounted, onUnmounted, reactive, ref } from 'vue'
import { ElMessageBox } from 'element-plus'
import V2Page from '@/components/v2/V2Page.vue'
import V2Section from '@/components/v2/V2Section.vue'
import V2StatusPill from '@/components/v2/V2StatusPill.vue'
import { usePermissions } from '@/composables/usePermissions'
import { createUser, deleteUser, getUsers, updateUser } from '@/api/users'
import { formatDateTime } from './helpers'

const { canManageUsers } = usePermissions()
const loading = ref(false)
const saving = ref(false)
const users = ref([])
const dialog = reactive({ visible: false, editing: null })
const form = reactive({ email: '', password: '', role: 'viewer', is_active: true })

onMounted(() => {
  fetchUsers()
  window.addEventListener('v2-open-user-create', openCreate)
})
onUnmounted(() => window.removeEventListener('v2-open-user-create', openCreate))

async function fetchUsers() {
  loading.value = true
  try {
    const response = await getUsers()
    users.value = response.data || []
  } finally {
    loading.value = false
  }
}

function openCreate() {
  dialog.editing = null
  Object.assign(form, { email: '', password: '', role: 'viewer', is_active: true })
  dialog.visible = true
}

function openEdit(user) {
  dialog.editing = user
  Object.assign(form, { email: user.email, password: '', role: user.role, is_active: user.is_active !== false })
  dialog.visible = true
}

async function saveUser() {
  saving.value = true
  try {
    if (dialog.editing) {
      await updateUser(dialog.editing.id, { email: form.email, role: form.role, is_active: form.is_active })
    } else {
      await createUser(form)
    }
    dialog.visible = false
    await fetchUsers()
  } finally {
    saving.value = false
  }
}

async function toggleUser(user) {
  await updateUser(user.id, { ...user, is_active: user.is_active === false })
  await fetchUsers()
}

async function handleDelete(user) {
  await ElMessageBox.confirm(`确定删除用户 ${user.email} 吗？`, '高风险操作', { type: 'warning' })
  await deleteUser(user.id)
  await fetchUsers()
}

function roleLabel(role) {
  return ({ admin: '管理员', operator: '操作员', viewer: '只读用户' })[role] || role
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.role-permission-list {
  display: grid;
  gap: 10px;
  border-radius: 22px;
  background: $v2-card-soft;
  padding: 14px;

  div {
    display: grid;
    grid-template-columns: 90px minmax(0, 1fr);
    gap: 12px;
    align-items: center;
    min-height: 38px;
  }

  strong {
    color: $v2-ink;
    font-weight: 950;
  }

  span {
    color: $v2-muted;
    font-weight: 800;
    line-height: 1.5;
  }
}

@media (max-width: 760px) {
  .role-permission-list div {
    grid-template-columns: 1fr;
    gap: 4px;
  }
}
</style>
