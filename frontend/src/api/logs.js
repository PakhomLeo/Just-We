import request from '@/utils/request'

export const getLogs = (params) => request.get('/logs/', { params })
export const getLogStats = () => request.get('/logs/stats')
