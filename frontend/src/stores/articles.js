import { defineStore } from 'pinia'
import { ref } from 'vue'
import { getArticles } from '@/api/articles'

export const useArticlesStore = defineStore('articles', () => {
  const articles = ref([])
  const loading = ref(false)
  const filters = ref({
    search: '',
    aiRatioMin: 0,
    aiRatioMax: 100
  })

  async function fetchArticles(params = {}) {
    loading.value = true
    try {
      const response = await getArticles(params)
      articles.value = response.data
    } finally {
      loading.value = false
    }
  }

  return {
    articles,
    loading,
    filters,
    fetchArticles
  }
})
