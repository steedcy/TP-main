import request from './request'

// 对应附录B 6.1节用户认证模块
export function login(data) {
  return request.post('/auth/login', data)
}

export function logout() {
  return request.post('/auth/logout')
}

export function unlockUser(userId) {
  return request.post(`/users/${userId}/unlock`)
}

export function listUsers(params) {
  return request.get('/users', { params })
}

export function createUser(data) {
  return request.post('/users', data)
}

export function resetPassword(userId, newPassword) {
  return request.post(`/users/${userId}/reset-password`, { newPassword })
}

export function updateUserStatus(userId, status) {
  return request.post(`/users/${userId}/status`, { status })
}
