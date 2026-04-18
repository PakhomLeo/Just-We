import request from '@/utils/request'

export const exportFeeds = (format = 'opml') => request.get('/feeds/export', {
  params: { format },
  responseType: 'blob'
})
