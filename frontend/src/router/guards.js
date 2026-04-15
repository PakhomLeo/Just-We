import router from './index'
import { useAuthStore } from '@/stores/auth'

const whiteList = ['/login']

router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  const requiresAuth = to.matched.some(record => record.meta.requiresAuth !== false)
  const requiresAdmin = to.matched.some(record => record.meta.requiresAdmin)

  if (requiresAuth && !authStore.token) {
    // Not authenticated, redirect to login
    next({ name: 'Login', query: { redirect: to.fullPath } })
    return
  }

  if (requiresAdmin && authStore.user?.role !== 'admin') {
    // Not admin, redirect to dashboard
    next({ name: 'Dashboard' })
    return
  }

  if (authStore.token && to.name === 'Login') {
    // Already authenticated, go to dashboard
    next({ name: 'Dashboard' })
    return
  }

  next()
})

export default router