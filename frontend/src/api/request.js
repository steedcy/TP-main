import axios from 'axios'
import { message } from 'ant-design-vue'
import router from '../router'
import { useAuthStore } from '../store/auth'

const request = axios.create({
  baseURL: '/api/v1',
  timeout: 65000 // 略大于规划模型60秒超时约束，避免代理层提前断开（对应部署实施手册6.3节）
})

request.interceptors.request.use((config) => {
  const authStore = useAuthStore()
  if (authStore.token) {
    config.headers.Authorization = `Bearer ${authStore.token}`
  }
  return config
})

request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const status = error.response?.status
    const code = error.response?.data?.code
    if (status === 401) {
      // code=2001会话已过期(空闲30分钟失效，对应SRS_NF002)、2000未提供有效Token，两者统一跳转登录页。
      // 已经在登录页时不重复提示/跳转，避免退出登录后残留的轮询定时器持续弹窗刷屏
      if (error.config?.url === '/auth/login') {
        message.error(error.response?.data?.message || '账号或密码错误')
      } else if (router.currentRoute.value.path !== '/login') {
        const authStore = useAuthStore()
        authStore.clear()
        message.warning(code === 2001 ? '登录已过期，请重新登录' : '请先登录')
        router.push('/login')
      }
    } else if (status === 403 && !error.config?.silent) {
      // 越权访问统一提示，后端已同步写入操作记录（对应5.1.1业务规则5）
      message.error('无权限访问，该操作需要更高权限角色')
    } else if (!error.config?.silent) {
      message.error(error.response?.data?.message || '请求失败，请稍后重试')
    }
    return Promise.reject(error)
  }
)

export default request
