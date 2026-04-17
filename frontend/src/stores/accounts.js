import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import { getAccounts } from '@/api/accounts'

export const useAccountsStore = defineStore('accounts', () => {
  const accounts = ref([])
  const loading = ref(false)
  const filters = ref({
    tier: null,
    status: null,
    search: ''
  })

  const filteredAccounts = computed(() => {
    return accounts.value.filter(account => {
      if (filters.value.tier && account.tier !== filters.value.tier) return false
      if (filters.value.status && account.status !== filters.value.status) return false
      if (filters.value.search) {
        const search = filters.value.search.toLowerCase()
        return account.name.toLowerCase().includes(search)
      }
      return true
    })
  })

  const stats = computed(() => ({
    total: accounts.value.length,
    active: accounts.value.filter(a => a.status === 'active').length,
    inactive: accounts.value.filter(a => a.status === 'inactive').length
  }))

  async function fetchAccounts() {
    loading.value = true
    try {
      const response = await getAccounts()
      accounts.value = response.data?.items || []
    } finally {
      loading.value = false
    }
  }

  return {
    accounts,
    loading,
    filters,
    filteredAccounts,
    stats,
    fetchAccounts
  }
})
