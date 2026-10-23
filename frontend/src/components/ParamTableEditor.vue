<template>
  <div>
    <a-table :dataSource="modelValue" :columns="columns" :pagination="false" rowKey="__key" size="small">
      <template #bodyCell="{ column, record, index }">
        <template v-if="column.key === 'name'">
          <a-input v-model:value="record.name" placeholder="参数名" size="small" />
        </template>
        <template v-else-if="column.key === 'type'">
          <a-select v-model:value="record.type" size="small" style="width: 100%">
            <a-select-option v-for="t in paramTypes" :key="t" :value="t">{{ t }}</a-select-option>
          </a-select>
        </template>
        <template v-else-if="column.key === 'required'">
          <a-checkbox v-model:checked="record.required" />
        </template>
        <template v-else-if="column.key === 'defaultValue'">
          <a-input v-model:value="record.defaultValue" placeholder="默认值" size="small" />
        </template>
        <template v-else-if="column.key === 'range'">
          <a-input v-model:value="record.range" placeholder="取值范围/说明" size="small" />
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button size="small" danger type="link" @click="removeRow(index)">删除</a-button>
        </template>
      </template>
    </a-table>
    <a-button type="dashed" block style="margin-top: 8px" @click="addRow">+ 添加参数</a-button>
  </div>
</template>

<script setup>
import { PARAM_TYPES } from '../constants/capability'

const props = defineProps({
  modelValue: { type: Array, required: true },
  mode: { type: String, default: 'input' } // input | output：输出参数不需要required/defaultValue/range
})
const emit = defineEmits(['update:modelValue'])
const paramTypes = PARAM_TYPES

const inputColumns = [
  { title: '参数名', key: 'name' },
  { title: '类型', key: 'type', width: 120 },
  { title: '必填', key: 'required', width: 70 },
  { title: '默认值', key: 'defaultValue' },
  { title: '取值范围/说明', key: 'range' },
  { title: '', key: 'action', width: 70 }
]
const outputColumns = [
  { title: '参数名', key: 'name' },
  { title: '类型', key: 'type', width: 120 },
  { title: '说明', key: 'range' },
  { title: '', key: 'action', width: 70 }
]
const columns = props.mode === 'output' ? outputColumns : inputColumns

let keySeq = 0
function addRow() {
  const rows = [...props.modelValue, { __key: `k${keySeq++}`, name: '', type: 'String', required: false, defaultValue: '', range: '' }]
  emit('update:modelValue', rows)
}
function removeRow(index) {
  const rows = props.modelValue.filter((_, i) => i !== index)
  emit('update:modelValue', rows)
}
</script>
