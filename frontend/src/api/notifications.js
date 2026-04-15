import request from '@/utils/request'

export const getNotifications = () => request.get('/notifications/')
export const markNotificationRead = (id) => request.post(`/notifications/${id}/read`)
