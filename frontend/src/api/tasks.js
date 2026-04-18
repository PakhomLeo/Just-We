import request from '@/utils/request'

export const triggerFetchTask = (monitoredAccountId) => request.post(`/tasks/fetch/${monitoredAccountId}`)
export const triggerAllFetchTasks = () => request.post('/tasks/fetch/all')
export const getFetchTaskStatus = (monitoredAccountId) => request.get(`/tasks/fetch/${monitoredAccountId}/status`)
