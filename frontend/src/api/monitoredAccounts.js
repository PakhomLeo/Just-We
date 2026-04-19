import request from '@/utils/request'

export const getMonitoredAccounts = () => request.get('/monitored-accounts/')
export const getMonitoredAccount = (id) => request.get(`/monitored-accounts/${id}`)
export const createMonitoredAccount = (data) => request.post('/monitored-accounts/', data)
export const updateMonitoredAccount = (id, data) => request.put(`/monitored-accounts/${id}`, data)
export const deleteMonitoredAccount = (id) => request.delete(`/monitored-accounts/${id}`)
export const triggerMonitoredFetch = (id) => request.post(`/monitored-accounts/${id}/fetch`)
export const triggerHistoryBackfill = (id) => request.post(`/monitored-accounts/${id}/history-backfill`)
export const getHistoryBackfillStatus = (id) => request.get(`/monitored-accounts/${id}/history-backfill/status`)
export const stopHistoryBackfill = (id) => request.post(`/monitored-accounts/${id}/history-backfill/stop`)
