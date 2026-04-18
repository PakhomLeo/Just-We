import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/v2/LoginV2.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/components/v2/V2AppShell.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/v2/DashboardV2.vue')
      },
      {
        path: 'accounts',
        name: 'Accounts',
        redirect: '/mp-accounts'
      },
      {
        path: 'mp-accounts',
        name: 'MpAccounts',
        component: () => import('@/views/v2/MonitoredAccountsV2.vue')
      },
      {
        path: 'articles',
        name: 'Articles',
        component: () => import('@/views/v2/ArticleListV2.vue')
      },
      {
        path: 'exports',
        name: 'ArticleExports',
        component: () => import('@/views/v2/ArticleExportV2.vue')
      },
      {
        path: 'articles/:id',
        name: 'ArticleDetail',
        component: () => import('@/views/v2/ArticleDetailV2.vue')
      },
      {
        path: 'proxies',
        name: 'Proxies',
        component: () => import('@/views/v2/ProxyManageV2.vue')
      },
      {
        path: 'weight',
        name: 'WeightConfig',
        component: () => import('@/views/v2/WeightConfigV2.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/v2/JobsLogsV2.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'capture-accounts',
        name: 'CaptureAccounts',
        component: () => import('@/views/v2/CollectorAccountsV2.vue')
      },
      {
        path: 'system-users',
        name: 'SystemUsers',
        component: () => import('@/views/v2/SystemUsersV2.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/v2/SystemSettingsV2.vue'),
        meta: { requiresAdmin: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

router.beforeEach(async (to) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin)

  if (authStore.token && !authStore.user) {
    await authStore.fetchUser()
  }

  if (requiresAuth && !authStore.isAuthenticated) {
    return { name: 'Login', query: { redirect: to.fullPath } }
  }
  if (requiresAdmin && authStore.user?.role !== 'admin') {
    return { name: 'Dashboard' }
  }
  if (to.name === 'Login' && authStore.isAuthenticated) {
    return { name: 'Dashboard' }
  }
  return true
})

export default router
