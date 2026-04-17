import request from '@/utils/request'

export const getFetchJobs = () => request.get('/fetch-jobs/')
