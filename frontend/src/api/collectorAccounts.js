import request from '@/utils/request'

export const getCollectorAccounts = () => request.get('/collector-accounts/')
export const deleteCollectorAccount = (id) => request.delete(`/collector-accounts/${id}`)
export const generateCollectorQRCode = (account_type) => request.post('/collector-accounts/qr/generate', { account_type })
export const getCollectorQRStatus = (ticket) => request.get('/collector-accounts/qr/status', { params: { ticket } })
export const cancelCollectorQRLogin = (ticket) => request.delete(`/collector-accounts/qr/${ticket}`)
export const healthCheckCollectorAccount = (id) => request.post(`/collector-accounts/${id}/health-check`)
