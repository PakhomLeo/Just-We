export function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}

export function formatPercent(value) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) return '-'
  return `${Math.round(Number(value) * 100)}%`
}

export function apiBaseUrl() {
  const apiBase = import.meta.env.VITE_API_BASE_URL || ''
  if (apiBase) return apiBase.replace(/\/api\/?$/, '')
  if (['localhost', '127.0.0.1'].includes(window.location.hostname) && window.location.port === '5173') {
    return `${window.location.protocol}//${window.location.hostname}:8000`
  }
  return window.location.origin
}

export function downloadBlob(response, filename, type = 'application/octet-stream') {
  const blob = new Blob([response.data], { type })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = filename
  link.click()
  URL.revokeObjectURL(url)
}

export function jsonText(value) {
  return JSON.stringify(value || {}, null, 2)
}

export function shortText(value, max = 72) {
  if (!value) return '-'
  const text = String(value)
  return text.length > max ? `${text.slice(0, max)}...` : text
}
