import { createRouter, createWebHistory } from 'vue-router'
import { useAuthStore } from '../store/auth'

const routes = [
  { path: '/login', name: 'Login', component: () => import('../views/auth/LoginView.vue'), meta: { public: true } },
  {
    path: '/',
    component: () => import('../layout/MainLayout.vue'),
    redirect: '/overview',
    children: [
      { path: 'overview', name: 'Overview', component: () => import('../views/task/OverviewView.vue') },
      { path: 'users', name: 'Users', component: () => import('../views/auth/UserManageView.vue'), meta: { roles: ['SYSTEM_ADMIN'] } },
      { path: 'devices', name: 'Devices', component: () => import('../views/device/DeviceListView.vue'), meta: { roles: ['CONFIG_ADMIN'] } },
      { path: 'simulators', name: 'Simulators', component: () => import('../views/simulator/SimulatorConsoleView.vue'), meta: { roles: ['CONFIG_ADMIN'] } },
      { path: 'devices/:deviceCode/capabilities', name: 'DeviceCapabilities', component: () => import('../views/device/DeviceCapabilityView.vue'), meta: { roles: ['CONFIG_ADMIN'] } },
      { path: 'device-agents', name: 'DeviceAgents', component: () => import('../views/device/DeviceAgentListView.vue') },
      { path: 'device-types', name: 'DeviceTypes', component: () => import('../views/devicetype/DeviceTypeBoundaryView.vue'), meta: { roles: ['CONFIG_ADMIN'] } },
      { path: 'baseline-templates', name: 'BaselineTemplates', component: () => import('../views/baseline/BaselineTemplateView.vue'), meta: { roles: ['CONFIG_ADMIN'] } },
      { path: 'task-definitions', name: 'TaskDefinitions', component: () => import('../views/taskdef/TaskDefinitionView.vue'), meta: { roles: ['CONFIG_ADMIN'] } },
      { path: 'risk-rules', name: 'RiskRules', component: () => import('../views/risk/RiskRuleView.vue'), meta: { roles: ['CONFIG_ADMIN'] } },
      { path: 'tasks', name: 'Tasks', component: () => import('../views/task/TaskListView.vue'), meta: { roles: ['OPERATOR'] } },
      { path: 'tasks/:taskId', name: 'TaskDetail', component: () => import('../views/task/TaskDetailView.vue'), meta: { roles: ['OPERATOR', 'SYSTEM_ADMIN'] } },
      { path: 'task-exceptions', name: 'TaskExceptions', component: () => import('../views/task/TaskExceptionListView.vue'), meta: { roles: ['SYSTEM_ADMIN', 'OPERATOR'] } },
      { path: 'task-trace', name: 'TaskTrace', component: () => import('../views/task/TaskTraceView.vue'), meta: { roles: ['SYSTEM_ADMIN', 'OPERATOR'] } },
      { path: 'situation', name: 'Situation', component: () => import('../views/situation/SituationView.vue') },
      { path: 'operation-logs', name: 'OperationLogs', component: () => import('../views/operation/OperationLogView.vue') }
    ]
  }
]

const router = createRouter({
  history: createWebHistory(),
  routes
})

// 前端路由守卫仅用于菜单/页面级体验优化，接口权限仍由后端逐接口校验（对应SRS_NF004），
// 不能把前端守卫当作唯一的权限边界。
router.beforeEach((to, from, next) => {
  const authStore = useAuthStore()
  if (to.meta.public) {
    return next()
  }
  if (!authStore.token) {
    return next('/login')
  }
  if (to.meta.roles && !to.meta.roles.includes(authStore.role)) {
    return next('/overview')
  }
  next()
})

export default router
