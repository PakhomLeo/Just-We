import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { login as apiLogin, register as apiRegister, getCurrentUser } from '@/api/auth'

export const useAuthStore = defineStore('auth', () => {
  const token = ref(localStorage.getItem('token') || '')
  const user = ref(null)

  const isAuthenticated = computed(() => !!token.value)
  const isAdmin = computed(() => user.value?.role === 'admin')

  async function login(credentials) {
    const response = await apiLogin(credentials)
    token.value = response.data.access_token
    localStorage.setItem('token', token.value)
    await fetchUser()
    return response
  }

  async function register(data) {
    await apiRegister(data)
    return await login({
      email: data.email,
      password: data.password
    })
  }

  async function fetchUser() {
    if (!token.value) return
    try {
      const response = await getCurrentUser()
      user.value = response.data
    } catch (error) {
      logout()
    }
  }

  function logout() {
    token.value = ''
    user.value = null
    localStorage.removeItem('token')
  }

  // Initialize user on store creation
  if (token.value) {
    fetchUser()
  }

  return {
    token,
    user,
    isAuthenticated,
    isAdmin,
    login,
    register,
    logout,
    fetchUser
  }
})
