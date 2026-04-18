import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, getCurrentUser } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)
  const initialized = ref(false)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(credentials) {
    const response = await apiLogin(credentials)
    token.value = response.data.access_token
    localStorage.setItem('token', token.value)
    await fetchUser({ force: true, throwOnError: true })
    return response
  }

  async function register(data) {
    await apiRegister(data)
    return await login({
      email: data.email,
      password: data.password
    })
  }

  async function fetchUser(options = {}) {
    if (!token.value) {
      user.value = null
      initialized.value = true
      return null
    }
    if (user.value && !options.force) {
      initialized.value = true
      return user.value
    }
    try {
      const response = await getCurrentUser()
      user.value = response.data
      initialized.value = true
      return user.value
    } catch (error) {
      logout()
      initialized.value = true
      if (options.throwOnError) {
        throw error
      }
      return null
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    initialized.value = true
    localStorage.removeItem('token')
  }

  // Initialize user on store creation
  if (token.value) {
    fetchUser()
  } else {
    initialized.value = true
  }

  return {
    token,
    user,
    initialized,
    isAuthenticated,
    isAdmin,
    login,
    register,
    logout,
    fetchUser
  }
})
