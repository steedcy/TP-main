<template>
  <div>
    <a-alert message="确定性高风险规则（对应TBD-03拍板结论），规则版本号只读，修改内容自动生成新版本" type="info" style="margin-bottom: 16px" />
    <a-space style="margin-bottom: 12px">
      <a-button type="primary" @click="openCreate" data-testid="risk-rule-create">新增规则</a-button>
    </a-space>
    <a-table :dataSource="rules" :columns="columns" rowKey="ruleCode">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'enabled'">
          <a-switch v-model:checked="record.enabled" @change="(val) => toggleEnabled(record, val)" />
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button size="small" @click="openEdit(record)">编辑规则内容</a-button>
        </template>
      </template>
    </a-table>

    <!-- 新增与编辑共用一个弹窗；编号只在新增时可填，编辑时只读（DEF-S3-042） -->
    <a-modal v-model:open="formVisible" :title="editing ? `编辑规则 ${form.ruleCode}` : '新增规则'"
             :confirmLoading="saving" ok-text="保存" @ok="save" @cancel="resetForm">
      <a-form layout="vertical">
        <a-form-item label="规则编号" :validate-status="errors.ruleCode ? 'error' : ''" :help="errors.ruleCode" required>
          <a-input v-model:value="form.ruleCode" :disabled="editing" :maxlength="64" data-testid="risk-rule-code" />
        </a-form-item>
        <a-form-item label="规则内容" :validate-status="errors.ruleContent ? 'error' : ''" :help="errors.ruleContent" required>
          <a-textarea v-model:value="form.ruleContent" :rows="4" :maxlength="1000" show-count data-testid="risk-rule-content" />
        </a-form-item>
        <a-form-item v-if="!editing" label="创建后立即启用">
          <a-switch v-model:checked="form.enabled" />
        </a-form-item>
      </a-form>
    </a-modal>
  </div>
</template>

<script setup>
import { onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import request from '../../api/request'
import { validateRuleForm } from '../../utils/riskRuleForm'

const rules = ref([])
const columns = [
  { title: '规则编号', dataIndex: 'ruleCode' },
  { title: '规则内容', dataIndex: 'ruleContent' },
  { title: '版本号', dataIndex: 'ruleVersion' },
  { title: '启用', key: 'enabled' },
  { title: '操作', key: 'action' }
]

const formVisible = ref(false)
const editing = ref(false)
const saving = ref(false)
const form = reactive({ ruleCode: '', ruleContent: '', enabled: true })
const errors = reactive({ ruleCode: '', ruleContent: '' })

function resetForm() {
  Object.assign(form, { ruleCode: '', ruleContent: '', enabled: true })
  Object.assign(errors, { ruleCode: '', ruleContent: '' })
}

function openCreate() {
  resetForm()
  editing.value = false
  formVisible.value = true
}

function openEdit(record) {
  resetForm()
  editing.value = true
  Object.assign(form, { ruleCode: record.ruleCode, ruleContent: record.ruleContent })
  formVisible.value = true
}

async function save() {
  const result = validateRuleForm(form, { editing: editing.value, existingCodes: rules.value.map((r) => r.ruleCode) })
  Object.assign(errors, { ruleCode: '', ruleContent: '' }, result.errors)
  if (!result.ok) return
  saving.value = true
  try {
    if (editing.value) {
      if (result.value.ruleContent === rules.value.find((r) => r.ruleCode === form.ruleCode)?.ruleContent) {
        message.info('规则内容没有变化')
        formVisible.value = false
        return
      }
      await request.post(`/risk-rules/${form.ruleCode}/update`, { ruleContent: result.value.ruleContent })
      message.success('规则已更新，版本号自动递增')
    } else {
      await request.post('/risk-rules', { ...result.value, enabled: form.enabled })
      message.success('规则已新增')
    }
    formVisible.value = false
    resetForm()
    await fetchList()
  } catch (e) {
    // 请求失败（如编号重复409）：全局拦截器已提示原因，弹窗保持打开以便修改后重试，不丢已填内容
  } finally {
    saving.value = false
  }
}

async function fetchList() {
  const resp = await request.get('/risk-rules')
  rules.value = resp.data
}

async function toggleEnabled(record, enabled) {
  try {
    await request.post(`/risk-rules/${record.ruleCode}/update`, { enabled })
    message.success('规则状态已更新')
  } catch (e) {
    record.enabled = !enabled
  }
}

onMounted(fetchList)
</script>
