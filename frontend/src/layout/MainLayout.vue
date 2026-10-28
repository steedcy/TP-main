<template>
  <a-layout style="min-height: 100vh">
    <a-layout-sider>
      <div class="logo">智慧机场AI协同平台</div>
      <a-menu theme="dark" mode="inline" :selectedKeys="[$route.name]">
        <a-menu-item key="Overview" @click="$router.push('/overview')">运行总览</a-menu-item>
        <a-menu-item key="Tasks" v-if="isOperator" @click="$router.push('/tasks')">任务管理</a-menu-item>
        <a-menu-item key="TaskExceptions" v-if="isOperator || isSystemAdmin" @click="$router.push('/task-exceptions')">异常处置</a-menu-item>
        <a-menu-item key="TaskTrace" v-if="isOperator || isSystemAdmin" @click="$router.push('/task-trace')">过程追溯</a-menu-item>
        <a-menu-item key="Situation" @click="$router.push('/situation')">二维态势</a-menu-item>
        <a-menu-item key="Devices" v-if="isConfigAdmin" @click="$router.push('/devices')">设备管理</a-menu-item>
        <a-menu-item key="Simulators" v-if="isConfigAdmin" @click="$router.push('/simulators')">仿真控制</a-menu-item>
        <a-menu-item key="DeviceAgents" @click="$router.push('/device-agents')">设备代理</a-menu-item>
        <a-menu-item key="DeviceTypes" v-if="isConfigAdmin" @click="$router.push('/device-types')">能力边界配置</a-menu-item>
        <a-menu-item key="BaselineTemplates" v-if="isConfigAdmin" @click="$router.push('/baseline-templates')">基线模板</a-menu-item>
        <a-menu-item key="TaskDefinitions" v-if="isConfigAdmin" @click="$router.push('/task-definitions')">任务定义</a-menu-item>
        <a-menu-item key="RiskRules" v-if="isConfigAdmin" @click="$router.push('/risk-rules')">风险规则配置</a-menu-item>
        <a-menu-item key="Users" v-if="isSystemAdmin" @click="$router.push('/users')">账号管理</a-menu-item>
        <a-menu-item key="DemoDataReset" v-if="isSystemAdmin" @click="$router.push('/demo-data-reset')">标准演示数据复位</a-menu-item>
        <a-menu-item key="OperationLogs" @click="$router.push('/operation-logs')">操作记录</a-menu-item>
      </a-menu>
    </a-layout-sider>
    <a-layout>
      <a-layout-header style="background: #fff; display: flex; justify-content: flex-end; align-items: center; padding: 0 24px">
        <span style="margin-right: 16px" data-testid="current-user">{{ authStore.username }}（{{ authStore.realName }}，{{ roleLabel }}）</span>
        <a-button @click="handleLogout">退出登录</a-button>
      </a-layout-header>
      <a-layout-content style="margin: 16px; background: #fff; padding: 16px">
        <router-view />
      </a-layout-content>
    </a-layout>
  </a-layout>
</template>

<script setup>
import { computed } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../store/auth'
import { logout } from '../api/auth'

const router = useRouter()
const authStore = useAuthStore()

const isSystemAdmin = computed(() => authStore.role === 'SYSTEM_ADMIN')
const isOperator = computed(() => authStore.role === 'OPERATOR')
const isConfigAdmin = computed(() => authStore.role === 'CONFIG_ADMIN')

const roleLabelMap = { SYSTEM_ADMIN: '系统管理员', OPERATOR: '运行操作员', CONFIG_ADMIN: '配置管理员' }
const roleLabel = computed(() => roleLabelMap[authStore.role] || authStore.role)

async function handleLogout() {
  await logout()
  authStore.clear()
  router.push('/login')
}
</script>

<style scoped>
.logo {
  color: #fff;
  padding: 16px;
  font-weight: bold;
  text-align: center;
}
</style>
