<template>
  <div>
    <a-alert
      message="确定性高风险规则由配置管理员维护并版本化（对应TBD-03拍板结论与5.4.5业务规则5）。规则修改或启停均自动生成新规则集版本。"
      type="info"
      style="margin-bottom: 16px"
    />

    <div style="margin-bottom: 16px; display: flex; justify-content: space-between; align-items: center">
      <a-button type="primary" @click="openCreateModal" data-testid="btn-create-risk-rule">
        新增规则
      </a-button>
      <span style="color: #666">
        当前规则集版本：<strong>{{ currentRuleSetVersion }}</strong>
      </span>
    </div>

    <a-table :dataSource="rules" :columns="columns" rowKey="ruleCode">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'enabled'">
          <a-switch
            v-model:checked="record.enabled"
            :loading="record._updating"
            @change="(val) => toggleEnabled(record, val)"
          />
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button size="small" @click="openEditModal(record)">编辑规则内容</a-button>
        </template>
      </template>
    </a-table>

    <!-- DEF-S3-042：新增规则表单模态框 -->
    <a-modal
      v-model:open="createVisible"
      title="新增确定性高风险规则"
      :confirmLoading="createLoading"
      @ok="handleCreate"
      @cancel="closeCreateModal"
    >
      <a-form :model="createForm" layout="vertical">
        <a-form-item label="规则编号" required extra="仅允许字母、数字、下划线及连字符，长度不超过64个字符">
          <a-input
            v-model:value="createForm.ruleCode"
            placeholder="例如：RULE_CUSTOM_CHECK"
            maxlength="64"
            data-testid="input-rule-code"
          />
        </a-form-item>
        <a-form-item label="规则内容" required extra="详细描述规则判定条件与边界，不超过1000个字符">
          <a-textarea
            v-model:value="createForm.ruleContent"
            placeholder="请输入规则内容与命中条件描述..."
            :rows="4"
            maxlength="1000"
            data-testid="input-rule-content"
          />
        </a-form-item>
        <a-form-item label="默认启用">
          <a-switch v-model:checked="createForm.enabled" data-testid="switch-rule-enabled" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 编辑规则内容模态框 -->
    <a-modal
      v-model:open="editVisible"
      :title="`编辑规则内容 - ${editingRule?.ruleCode}`"
      :confirmLoading="editLoading"
      @ok="handleEdit"
      @cancel="editVisible = false"
    >
      <a-form layout="vertical">
        <a-form-item label="当前版本">
          <span>{{ editingRule?.ruleVersion }}</span>
        </a-form-item>
        <a-form-item label="规则内容" required extra="修改内容将使规则版本递增并更新规则集版本">
          <a-textarea
            v-model:value="editContent"
            placeholder="请输入规则内容..."
            :rows="4"
            maxlength="1000"
          />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import request from '../../api/request'

const rules = ref([])
const columns = [
  { title: '规则编号', dataIndex: 'ruleCode', key: 'ruleCode' },
  { title: '规则内容', dataIndex: 'ruleContent', key: 'ruleContent' },
  { title: '版本号', dataIndex: 'ruleVersion', key: 'ruleVersion' },
  { title: '启用', key: 'enabled' },
  { title: '操作', key: 'action' }
]

const currentRuleSetVersion = computed(() => {
  const seeded = new Set(['RULE_ESCORT_SPECIAL_PASSENGER', 'RULE_CROSS_ZONE', 'RULE_RESOURCE_CRITICAL'])
  let changes = 0
  for (const r of rules.value) {
    const vStr = (r.ruleVersion || 'V1.0').replace('V', '')
    const vNum = parseFloat(vStr) || 1.0
    const minor = Math.max(0, Math.round((vNum - 1.0) * 10))
    changes += minor
    if (r.ruleCode && !seeded.has(r.ruleCode)) {
      changes += 1
    }
  }
  return `V1.${changes}`
})

async function fetchList() {
  try {
    const resp = await request.get('/risk-rules')
    rules.value = resp.data || []
  } catch (err) {
    message.error(err.message || '获取规则列表失败')
  }
}

async function toggleEnabled(record, enabled) {
  record._updating = true
  try {
    const resp = await request.post(`/risk-rules/${record.ruleCode}/update`, { enabled })
    if (resp.data) {
      record.ruleVersion = resp.data.ruleVersion
      record.enabled = resp.data.enabled
    }
    message.success(`规则 ${record.ruleCode} 状态已更新，版本号已递增`)
    await fetchList()
  } catch (err) {
    record.enabled = !enabled
    message.error(err.message || '更新规则状态失败')
  } finally {
    record._updating = false
  }
}

// 新增规则模态框
const createVisible = ref(false)
const createLoading = ref(false)
const createForm = reactive({
  ruleCode: '',
  ruleContent: '',
  enabled: true
})

function openCreateModal() {
  createForm.ruleCode = ''
  createForm.ruleContent = ''
  createForm.enabled = true
  createVisible.value = true
}

function closeCreateModal() {
  createVisible.value = false
}

async function handleCreate() {
  const code = (createForm.ruleCode || '').trim()
  const content = (createForm.ruleContent || '').trim()
  if (!code) {
    message.warning('请输入规则编号')
    return
  }
  if (!content) {
    message.warning('请输入规则内容')
    return
  }
  createLoading.value = true
  try {
    await request.post('/risk-rules', {
      ruleCode: code,
      ruleContent: content,
      enabled: createForm.enabled
    })
    message.success('新规则创建成功，规则集版本已更新')
    createVisible.value = false
    await fetchList()
  } catch (err) {
    message.error(err.message || '创建规则失败')
  } finally {
    createLoading.value = false
  }
}

// 编辑规则模态框
const editVisible = ref(false)
const editLoading = ref(false)
const editingRule = ref(null)
const editContent = ref('')

function openEditModal(record) {
  editingRule.value = record
  editContent.value = record.ruleContent || ''
  editVisible.value = true
}

async function handleEdit() {
  if (!editingRule.value) return
  const content = (editContent.value || '').trim()
  if (!content) {
    message.warning('规则内容不能为空')
    return
  }
  editLoading.value = true
  try {
    await request.post(`/risk-rules/${editingRule.value.ruleCode}/update`, {
      ruleContent: content
    })
    message.success('规则已更新，版本号自动递增')
    editVisible.value = false
    await fetchList()
  } catch (err) {
    message.error(err.message || '修改规则内容失败')
  } finally {
    editLoading.value = false
  }
}

onMounted(fetchList)
</script>
