import request from '@/utils/request'

export const getProxies = (params) => request.get('/proxies/', { params })
export const getProxyStats = () => request.get('/proxies/stats')
export const addProxy = (data) => request.post('/proxies/', data)
export const bulkAddProxies = (data) => request.post('/proxies/bulk', data)
export const updateProxy = (id, data) => request.put(`/proxies/${id}`, data)
export const deleteProxy = (id) => request.delete(`/proxies/${id}`)
export const checkProxy = (id) => request.post(`/proxies/${id}/test`)
export const getProxyServices = (id) => request.get(`/proxies/${id}/services`)
export const updateProxyServices = (id, data) => request.put(`/proxies/${id}/services`, data)
