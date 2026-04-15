import request from '@/utils/request'

export const getProxies = (type, params) => request.get(`/proxies/${type}`, { params })
export const getProxyStats = () => request.get('/proxies/stats')
export const addProxy = (data) => request.post('/proxies/', data)
export const deleteProxy = (id) => request.delete(`/proxies/${id}`)
export const checkProxy = (id) => request.post(`/proxies/${id}/check`)
