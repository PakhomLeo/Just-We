import request from '@/utils/request'

export const getArticleExports = (params) => request.get('/article-exports/', { params })
export const createArticleExport = (data) => request.post('/article-exports/', data)
export const downloadArticleExport = (id) => request.get(`/article-exports/${id}/download`, { responseType: 'blob' })
