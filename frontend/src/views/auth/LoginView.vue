<template>
  <div class="login-container">
    <a-card title="智慧机场人工智能集群协同服务平台" style="width: 400px">
      <a-form :model="form" @finish="handleLogin">
        <a-form-item name="username" :rules="[{ required: true, message: '请输入账号' }]">
          <a-input v-model:value="form.username" placeholder="账号" size="large" maxlength="32" />
        </a-form-item>
        <a-form-item name="password" :rules="[{ required: true, message: '请输入密码' }]">
          <a-input-password v-model:value="form.password" placeholder="密码" size="large" maxlength="32" />
        </a-form-item>
        <a-form-item>
          <a-button
            type="primary" html-type="submit" block size="large" :loading="loading"
            :disabled="!form.username || !form.password"
          >
            登录
          </a-button>
        </a-form-item>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { message } from 'ant-design-vue'
import { login } from '../../api/auth'
import { useAuthStore } from '../../store/auth'

const router = useRouter()
const authStore = useAuthStore()
const loading = ref(false)
const form = reactive({ username: '', password: '' })

async function handleLogin() {
  loading.value = true
  try {
    const resp = await login(form)
    // 统一提示"登录成功"，不区分之前是否有失败尝试；失败时统一提示由request.js的错误拦截器和
    // 后端统一错误码2002/2004/2005/2006处理，前端不做额外的"剩余次数"提示（对应5.1.1业务规则、TC_AUTH_002/004）
    authStore.setSession(resp.data)
    router.push('/overview')
  } catch (e) {
    // 错误提示已由request.js统一处理并message.error展示，此处无需重复提示
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-container {
  height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #1a2a6c, #2c5364);
}
</style>
