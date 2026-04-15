import request from '@/utils/request'

export const getWeightConfig = () => request.get('/weight/')
export const updateWeightConfig = (data) => request.put('/weight/', data)
export const testWeightFormula = (data) => request.post('/weight/test', data)
