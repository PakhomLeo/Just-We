import { computed } from 'vue'
import { useAuthStore } from '@/stores/auth'

export function usePermissions() {
  const authStore = useAuthStore()

  const isAdmin = computed(() => authStore.user?.role === 'admin')
  const isOperator = computed(() => authStore.user?.role === 'operator')
  const isViewer = computed(() => authStore.user?.role === 'viewer')

  const canManageWeight = computed(() => isAdmin.value)
  const canManageUsers = computed(() => isAdmin.value)
  const canViewLogs = computed(() => isAdmin.value)
  const canManageSettings = computed(() => isAdmin.value)
  const canManageAccounts = computed(() => isAdmin.value || isOperator.value)

  return {
    isAdmin,
    isOperator,
    isViewer,
    canManageWeight,
    canManageUsers,
    canViewLogs,
    canManageSettings,
    canManageAccounts
  }
}
