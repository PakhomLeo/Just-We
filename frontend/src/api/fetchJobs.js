import request from '@/utils/request'

export const getFetchJobs = () => request.get('/fetch-jobs/')
export const deleteFetchJob = (id) => request.delete(`/fetch-jobs/${id}`)
