import request from '@/utils/request'

export const getAccounts = (params) => request.get('/accounts/', { params })
export const getAccount = (id) => request.get(`/accounts/${id}`)
export const createAccount = (data) => request.post('/accounts/', data)
export const updateAccount = (id, data) => request.put(`/accounts/${id}`, data)
export const deleteAccount = (id) => request.delete(`/accounts/${id}`)
export const triggerCrawl = (id) => request.post(`/accounts/${id}/crawl`)
