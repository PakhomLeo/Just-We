import request from '@/utils/request'

export const triggerFetchTask = (accountId) => request.post(`/tasks/fetch/${accountId}`)
export const triggerAllFetchTasks = () => request.post('/tasks/fetch/all')
export const getFetchTaskStatus = (accountId) => request.get(`/tasks/fetch/${accountId}/status`)
