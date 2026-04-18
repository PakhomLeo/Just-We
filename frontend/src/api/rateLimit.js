import request from '@/utils/request'

export const getRateLimitStats = () => request.get('/rate-limit/stats')
