import request from '@/utils/request'

export const getArticles = (params) => request.get('/articles/', { params })
export const getArticle = (id) => request.get(`/articles/${id}`)
export const deleteArticle = (id) => request.delete(`/articles/${id}`)
export const reanalyzeArticleAI = (id) => request.post(`/articles/${id}/reanalyze-ai`)
export const getArticlesByMonitoredAccount = (id, params) => request.get(`/articles/monitored/${id}`, { params })
