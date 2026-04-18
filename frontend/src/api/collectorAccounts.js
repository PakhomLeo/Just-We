import request from '@/utils/request'

export const getCollectorAccounts = () => request.get('/collector-accounts/')
export const deleteCollectorAccount = (id) => request.delete(`/collector-accounts/${id}`)
export const generateCollectorQRCode = (accountType, loginProxyId) => request.post('/collector-accounts/qr/generate', { type: accountType, login_proxy_id: loginProxyId })
export const getCollectorQRStatus = (ticket) => request.get('/collector-accounts/qr/status', { params: { ticket } })
export const cancelCollectorQRLogin = (ticket) => request.delete(`/collector-accounts/qr/${ticket}`)
export const healthCheckCollectorAccount = (id) => request.post(`/collector-accounts/${id}/health-check`)
export const discoverCollectorFakeid = (id) => request.post(`/collector-accounts/${id}/discover-fakeid`)
export const updateCollectorLoginProxy = (id, loginProxyId) => request.put(`/collector-accounts/${id}/login-proxy`, { login_proxy_id: loginProxyId })
