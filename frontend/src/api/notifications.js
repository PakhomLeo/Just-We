import request from '@/utils/request'

export const getNotifications = (params) => request.get('/notifications/', { params })
export const markNotificationRead = (id) => request.put(`/notifications/${id}/read`)
export const markAllNotificationsRead = () => request.put('/notifications/read-all')
export const deleteNotification = (id) => request.delete(`/notifications/${id}`)
