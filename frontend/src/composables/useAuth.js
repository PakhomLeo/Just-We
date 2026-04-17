import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'
import { useRouter } from 'vue-router'

/**
 * 认证逻辑 composable
 * 提供认证相关的状态和操作
 */
export function useAuth() {
  const authStore = useAuthStore()
  const router = useRouter()

  // 认证状态
  const isAuthenticated = computed(() => authStore.isAuthenticated)
  const isAdmin = computed(() => authStore.isAdmin)
  const currentUser = computed(() => authStore.user)
  const token = computed(() => authStore.token)

  // 角色检查
  const userRole = computed(() => authStore.user?.role)

  /**
   * 检查是否拥有指定角色
   * @param {string|string[]} roles 角色名或角色数组
   * @returns {boolean}
   */
  function hasRole(roles) {
    if (!currentUser.value) return false
    const userRoleValue = currentUser.value.role
    if (Array.isArray(roles)) {
      return roles.includes(userRoleValue)
    }
    return userRoleValue === roles
  }

  /**
   * 检查是否是管理员
   * @returns {boolean}
   */
  function isAdminUser() {
    return currentUser.value?.role === 'admin'
  }

  /**
   * 检查是否是操作员
   * @returns {boolean}
   */
  function isOperator() {
    return currentUser.value?.role === 'operator'
  }

  /**
   * 检查是否是查看者
   * @returns {boolean}
   */
  function isViewer() {
    return currentUser.value?.role === 'viewer'
  }

  /**
   * 登录
   * @param {Object} credentials 凭据 { email, password }
   * @returns {Promise}
   */
  async function login(credentials) {
    try {
      const response = await authStore.login(credentials)
      return { success: true, data: response }
    } catch (error) {
      return { success: false, error: error.message || '登录失败' }
    }
  }

  /**
   * 注册
   * @param {Object} data 注册数据 { email, password }
   * @returns {Promise}
   */
  async function register(data) {
    try {
      const response = await authStore.register(data)
      return { success: true, data: response }
    } catch (error) {
      return { success: false, error: error.message || '注册失败' }
    }
  }

  /**
   * 登出
   */
  function logout() {
    authStore.logout()
    router.push({ name: 'Login' })
  }

  /**
   * 刷新用户信息
   */
  async function fetchUser() {
    await authStore.fetchUser()
  }

  return {
    // 状态
    isAuthenticated,
    isAdmin,
    currentUser,
    token,
    userRole,
    // 方法
    hasRole,
    isAdminUser,
    isOperator,
    isViewer,
    login,
    register,
    logout,
    fetchUser
  }
}
