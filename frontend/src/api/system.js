import request from '@/utils/request'

export const getAIConfig = () => request.get('/system/ai-config')
export const updateAIConfig = (data) => request.put('/system/ai-config', data)
export const getFetchPolicy = () => request.get('/system/fetch-policy')
export const updateFetchPolicy = (data) => request.put('/system/fetch-policy', data)
export const getRateLimitPolicy = () => request.get('/system/rate-limit-policy')
export const updateRateLimitPolicy = (data) => request.put('/system/rate-limit-policy', data)
export const getProxyPolicy = () => request.get('/system/proxy-policy')
export const updateProxyPolicy = (data) => request.put('/system/proxy-policy', data)
export const getNotificationEmailConfig = () => request.get('/system/notification-email')
export const updateNotificationEmailConfig = (data) => request.put('/system/notification-email', data)
export const getNotificationPolicy = () => request.get('/system/notification-policy')
export const updateNotificationPolicy = (data) => request.put('/system/notification-policy', data)
