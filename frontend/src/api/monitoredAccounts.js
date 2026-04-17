import request from '@/utils/request'

export const getMonitoredAccounts = () => request.get('/monitored-accounts/')
export const getMonitoredAccount = (id) => request.get(`/monitored-accounts/${id}`)
export const createMonitoredAccount = (data) => request.post('/monitored-accounts/', data)
export const updateMonitoredAccount = (id, data) => request.put(`/monitored-accounts/${id}`, data)
export const triggerMonitoredFetch = (id) => request.post(`/monitored-accounts/${id}/fetch`)
