import request from '@/utils/request'

export const getWeightConfig = () => request.get('/weight/config')
export const updateWeightConfig = (data) => request.put('/weight/config', data)
export const testWeightFormula = (data) => request.post('/weight/simulate', data)
