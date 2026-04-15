import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const routes = [
  {
    path: '/login',
    name: 'Login',
    component: () => import('@/views/auth/Login.vue'),
    meta: { requiresAuth: false }
  },
  {
    path: '/',
    component: () => import('@/components/layout/AppLayout.vue'),
    meta: { requiresAuth: true },
    children: [
      {
        path: '',
        redirect: '/dashboard'
      },
      {
        path: 'dashboard',
        name: 'Dashboard',
        component: () => import('@/views/dashboard/Dashboard.vue')
      },
      {
        path: 'accounts',
        name: 'Accounts',
        component: () => import('@/views/accounts/AccountList.vue')
      },
      {
        path: 'articles',
        name: 'Articles',
        component: () => import('@/views/articles/ArticleList.vue')
      },
      {
        path: 'articles/:id',
        name: 'ArticleDetail',
        component: () => import('@/views/articles/ArticleDetail.vue')
      },
      {
        path: 'proxies',
        name: 'Proxies',
        component: () => import('@/views/proxies/ProxyManage.vue')
      },
      {
        path: 'weight',
        name: 'WeightConfig',
        component: () => import('@/views/weight/WeightConfig.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'logs',
        name: 'Logs',
        component: () => import('@/views/logs/LogsMonitor.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'users',
        name: 'Users',
        component: () => import('@/views/users/UserManage.vue'),
        meta: { requiresAdmin: true }
      },
      {
        path: 'settings',
        name: 'Settings',
        component: () => import('@/views/settings/SystemSettings.vue'),
        meta: { requiresAdmin: true }
      }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

export default router