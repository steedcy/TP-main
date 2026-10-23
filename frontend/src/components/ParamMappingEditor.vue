<template>
  <div>
    <a-table :dataSource="modelValue" :columns="columns" :pagination="false" rowKey="__key" size="small">
      <template #bodyCell="{ column, record, index }">
        <template v-if="column.key === 'target'">
          <a-input v-model:value="record.target" placeholder="本步骤能力输入参数名" size="small" />
        </template>
        <template v-else-if="column.key === 'source'">
          <a-input v-model:value="record.source" placeholder="TEMPLATE_INPUT.xxx 或 STEP1_OUTPUT.xxx" size="small" />
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button size="small" danger type="link" @click="removeRow(index)">删除</a-button>
        </template>
      </template>
    </a-table>
    <a-button type="dashed" block style="margin-top: 8px" @click="addRow">+ 添加参数映射</a-button>
  </div>
</template>

<script setup>
const props = defineProps({
  modelValue: { type: Array, required: true }
})
const emit = defineEmits(['update:modelValue'])

const columns = [
  { title: '本步骤参数(target)', key: 'target' },
  { title: '来源(source)', key: 'source' },
  { title: '', key: 'action', width: 70 }
]

let keySeq = 0
function addRow() {
  emit('update:modelValue', [...props.modelValue, { __key: `m${keySeq++}`, target: '', source: '' }])
}
function removeRow(index) {
  emit('update:modelValue', props.modelValue.filter((_, i) => i !== index))
}
</script>
