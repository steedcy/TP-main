<template>
  <div>
    <a-alert message="三条确定性高风险规则（对应TBD-03拍板结论），规则版本号只读，修改内容自动生成新版本" type="info" style="margin-bottom: 16px" />
    <a-table :dataSource="rules" :columns="columns" rowKey="ruleCode">
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'enabled'">
          <a-switch v-model:checked="record.enabled" @change="(val) => toggleEnabled(record, val)" />
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button size="small" @click="editRule(record)">编辑规则内容</a-button>
        </template>
      </template>
    </a-table>
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { message } from 'ant-design-vue'
import request from '../../api/request'

const rules = ref([])
const columns = [
  { title: '规则编号', dataIndex: 'ruleCode' },
  { title: '规则内容', dataIndex: 'ruleContent' },
  { title: '版本号', dataIndex: 'ruleVersion' },
  { title: '启用', key: 'enabled' },
  { title: '操作', key: 'action' }
]

async function fetchList() {
  const resp = await request.get('/risk-rules')
  rules.value = resp.data
}

async function toggleEnabled(record, enabled) {
  await request.post(`/risk-rules/${record.ruleCode}/update`, { enabled })
  message.success('规则状态已更新')
}

function editRule(record) {
  const content = prompt('编辑规则内容', record.ruleContent)
  if (content && content !== record.ruleContent) {
    request.post(`/risk-rules/${record.ruleCode}/update`, { ruleContent: content }).then(() => {
      message.success('规则已更新，版本号自动递增')
      fetchList()
    })
  }
}

onMounted(fetchList)
</script>
