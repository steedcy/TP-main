import { defineStore } from 'pinia'

// 三类角色：SYSTEM_ADMIN/OPERATOR/CONFIG_ADMIN（对应V1.4正文5.1.1）
export const useAuthStore = defineStore('auth', {
  state: () => ({
    token: localStorage.getItem('token') || '',
    userId: Number(localStorage.getItem('userId')) || null,
    username: localStorage.getItem('username') || '',
    realName: localStorage.getItem('realName') || '',
    role: localStorage.getItem('role') || ''
  }),
  actions: {
    setSession({ token, user }) {
      this.token = token
      this.userId = user.id
      this.username = user.username
      this.realName = user.realName
      this.role = user.role
      localStorage.setItem('token', token)
      localStorage.setItem('userId', user.id)
      localStorage.setItem('username', user.username)
      localStorage.setItem('realName', user.realName)
      localStorage.setItem('role', user.role)
    },
    clear() {
      this.token = ''
      this.userId = null
      this.username = ''
      this.realName = ''
      this.role = ''
      localStorage.clear()
    }
  }
})
