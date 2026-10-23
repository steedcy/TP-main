<template>
  <div>
    <a-space style="margin-bottom: 16px">
      <a-select v-model:value="filterStatus" style="width: 160px" placeholder="按状态筛选" allow-clear @change="fetchList">
        <a-select-option value="ACTIVE">正常</a-select-option>
        <a-select-option value="LOCKED">已锁定</a-select-option>
        <a-select-option value="INACTIVE">已停用</a-select-option>
      </a-select>
      <a-button type="primary" @click="createVisible = true">新增账号</a-button>
    </a-space>

    <a-table :dataSource="list" :columns="columns" rowKey="id" :pagination="pagination" @change="handleTableChange">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'status'">
          <a-tag :color="statusColor(record.status)">{{ statusLabel(record.status) }}</a-tag>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-space>
            <a-popconfirm title="确认解锁该账号？" @confirm="handleUnlock(record.id)" v-if="record.status === 'LOCKED'">
              <a-button size="small" type="link">解锁</a-button>
            </a-popconfirm>
            <a-button size="small" type="link" @click="openResetPassword(record.id)">重置密码</a-button>
            <a-popconfirm
              v-if="record.status !== 'LOCKED'"
              :title="record.status === 'ACTIVE' ? '确认停用该账号？' : '确认启用该账号？'"
              @confirm="handleToggleStatus(record)"
            >
              <a-button size="small" type="link" danger>{{ record.status === 'ACTIVE' ? '停用' : '启用' }}</a-button>
            </a-popconfirm>
            <!-- 锁定账号需先解锁才能停用/启用，避免LOCKED被直接改写为INACTIVE导致锁定原因丢失 -->
            <a-tooltip v-else title="锁定账号需先解锁">
              <a-button size="small" type="link" disabled>停用</a-button>
            </a-tooltip>
          </a-space>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="createVisible" title="新增账号" @ok="handleCreate" :confirmLoading="createLoading">
      <a-form ref="createFormRef" :model="createForm" :rules="createRules" layout="vertical">
        <a-form-item label="账号" name="username">
          <a-input v-model:value="createForm.username" maxlength="32" placeholder="1~32位，系统内唯一" />
        </a-form-item>
        <a-form-item label="初始密码" name="password">
          <a-input-password v-model:value="createForm.password" maxlength="32" placeholder="8~32位" />
        </a-form-item>
        <a-form-item label="姓名" name="realName">
          <a-input v-model:value="createForm.realName" maxlength="32" />
        </a-form-item>
        <a-form-item label="角色" name="role">
          <a-select v-model:value="createForm.role">
            <a-select-option value="SYSTEM_ADMIN">系统管理员</a-select-option>
            <a-select-option value="OPERATOR">运行操作员</a-select-option>
            <a-select-option value="CONFIG_ADMIN">配置管理员</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="联系方式" name="contact">
          <a-input v-model:value="createForm.contact" placeholder="手机号或邮箱" />
        </a-form-item>
      </a-form>
    </a-modal>

    <a-modal
      v-model:open="resetPasswordVisible"
      title="重置密码"
      @ok="handleResetPassword"
      :confirmLoading="resetPasswordLoading"
    >
      <a-form ref="resetPasswordFormRef" :model="resetPasswordForm" :rules="resetPasswordRules" layout="vertical">
        <a-form-item label="新密码" name="newPassword">
          <a-input-password v-model:value="resetPasswordForm.newPassword" maxlength="32" placeholder="8~32位" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import { listUsers, createUser, unlockUser, updateUserStatus, resetPassword } from '../../api/auth'

const list = ref([])
const filterStatus = ref(undefined)
const pagination = reactive({ current: 1, pageSize: 20, total: 0 })

const createVisible = ref(false)
const createLoading = ref(false)
const createFormRef = ref(null)
const createForm = reactive({ username: '', password: '', realName: '', role: 'OPERATOR', contact: '' })
// 字段约束对应附录B 6.2.1节：账号1~32位、密码8~32位、姓名1~32位
const createRules = {
  username: [{ required: true, message: '请输入账号' }, { max: 32, message: '账号最长32位' }],
  password: [
    { required: true, message: '请输入初始密码' },
    { min: 8, max: 32, message: '密码长度需为8~32位' }
  ],
  realName: [{ required: true, message: '请输入姓名' }],
  role: [{ required: true, message: '请选择角色' }],
  contact: [{ required: true, message: '请输入联系方式' }]
}

const resetPasswordVisible = ref(false)
const resetPasswordLoading = ref(false)
const resetPasswordFormRef = ref(null)
const resetPasswordForm = reactive({ userId: null, newPassword: '' })
const resetPasswordRules = {
  newPassword: [
    { required: true, message: '请输入新密码' },
    { min: 8, max: 32, message: '密码长度需为8~32位' }
  ]
}

const columns = [
  { title: '账号', dataIndex: 'username' },
  { title: '姓名', dataIndex: 'realName' },
  { title: '角色', dataIndex: 'role' },
  { title: '联系方式', dataIndex: 'contact' },
  { title: '状态', key: 'status' },
  { title: '最后登录时间', dataIndex: 'lastLoginAt' },
  { title: '操作', key: 'action' }
]

function statusLabel(status) {
  return { ACTIVE: '正常', LOCKED: '已锁定', INACTIVE: '已停用' }[status] || status
}
function statusColor(status) {
  return { ACTIVE: 'green', LOCKED: 'red', INACTIVE: 'default' }[status]
}

async function fetchList() {
  const resp = await listUsers({ status: filterStatus.value, page: pagination.current, size: pagination.pageSize })
  list.value = resp.data.content
  pagination.total = resp.data.totalElements
}

function handleTableChange(pag) {
  pagination.current = pag.current
  fetchList()
}

async function handleUnlock(userId) {
  await unlockUser(userId)
  message.success('账号已解锁')
  fetchList()
}

async function handleToggleStatus(record) {
  const newStatus = record.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
  await updateUserStatus(record.id, newStatus)
  message.success('操作成功')
  fetchList()
}

function openResetPassword(userId) {
  resetPasswordForm.userId = userId
  resetPasswordForm.newPassword = ''
  resetPasswordVisible.value = true
}

async function handleResetPassword() {
  try {
    await resetPasswordFormRef.value.validate()
  } catch {
    return
  }
  resetPasswordLoading.value = true
  try {
    await resetPassword(resetPasswordForm.userId, resetPasswordForm.newPassword)
    message.success('密码已重置')
    resetPasswordVisible.value = false
  } finally {
    resetPasswordLoading.value = false
  }
}

async function handleCreate() {
  try {
    await createFormRef.value.validate()
  } catch {
    return
  }
  createLoading.value = true
  try {
    await createUser(createForm)
    message.success('账号创建成功')
    createVisible.value = false
    Object.assign(createForm, { username: '', password: '', realName: '', role: 'OPERATOR', contact: '' })
    fetchList()
  } finally {
    createLoading.value = false
  }
}

onMounted(fetchList)
</script>
