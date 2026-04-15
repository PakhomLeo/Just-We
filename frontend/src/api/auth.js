import axios from 'axios'

const apiClient = axios.create({
  baseURL: '/api',
  headers: {
    'Content-Type': 'application/json'
  }
})

// Add auth token to requests if available
apiClient.interceptors.request.use(config => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

export async function login(credentials) {
  const response = await apiClient.post('/auth/login', credentials)
  return response
}

export async function register(data) {
  const response = await apiClient.post('/auth/register', data)
  return response
}

export async function getCurrentUser() {
  const response = await apiClient.get('/auth/me')
  return response
}

export default {
  login,
  register,
  getCurrentUser
}
