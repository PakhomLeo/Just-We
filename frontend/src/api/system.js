import request from '@/utils/request'

export const getAIConfig = () => request.get('/system/ai-config')
export const updateAIConfig = (data) => request.put('/system/ai-config', data)
export const getFetchPolicy = () => request.get('/system/fetch-policy')
export const updateFetchPolicy = (data) => request.put('/system/fetch-policy', data)
export const getNotificationEmailConfig = () => request.get('/system/notification-email')
export const updateNotificationEmailConfig = (data) => request.put('/system/notification-email', data)
