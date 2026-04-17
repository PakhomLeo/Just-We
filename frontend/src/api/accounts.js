import request from '@/utils/request'

export const getAccounts = (params) => request.get('/accounts/', { params })
export const getAccount = (id) => request.get(`/accounts/${id}`)
export const createAccount = (data) => request.post('/accounts/', data)
export const updateAccount = (id, data) => request.put(`/accounts/${id}`, data)
export const deleteAccount = (id) => request.delete(`/accounts/${id}`)
export const triggerCrawl = (id) => request.post(`/accounts/${id}/crawl`)
export const applyOverride = (id, data) => request.post(`/accounts/${id}/override`, data)

// Health Check APIs
export const healthCheck = (id) => request.post(`/accounts/${id}/health-check`)
export const batchHealthCheck = (params) => request.post('/accounts/batch-health-check', {}, { params })

// QR Login APIs
export const generateQRCode = (type) => request.post('/accounts/qr/generate', { type })
export const getQRStatus = (ticket) => request.get('/accounts/qr/status', { params: { ticket } })
export const cancelQRLogin = (ticket) => request.delete(`/accounts/qr/${ticket}`)
