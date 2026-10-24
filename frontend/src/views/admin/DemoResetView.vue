<template>
  <div>
    <a-card title="F2 标准演示数据复位" :loading="loading">
      <a-alert v-if="!preview?.enabled" type="warning" show-icon
               message="当前环境未启用复位"
               description="仅隔离演示环境可设置 DEMO_RESET_ENABLED=true。当前共享测试数据不会变更。" />
      <template v-if="preview">
        <a-descriptions bordered :column="1" style="margin-top: 16px">
          <a-descriptions-item label="数据集版本">{{ preview.version }}</a-descriptions-item>
          <a-descriptions-item label="生成时间">{{ preview.generatedAt }}</a-descriptions-item>
          <a-descriptions-item label="源数据 SHA-256"><code>{{ preview.sourceDigest }}</code></a-descriptions-item>
          <a-descriptions-item label="当前业务数据摘要"><code>{{ preview.currentContentDigest }}</code></a-descriptions-item>
          <a-descriptions-item label="影响范围">{{ preview.impactScope.join('；') }}</a-descriptions-item>
          <a-descriptions-item label="保留范围">{{ preview.preservedScope.join('；') }}</a-descriptions-item>
          <a-descriptions-item label="复位后状态">{{ preview.postResetState }}</a-descriptions-item>
        </a-descriptions>
        <a-alert v-if="preview.blockingTasks.length || preview.busyDemoAgents.length" type="error" show-icon
                 style="margin-top: 16px" message="复位被活动任务或忙碌代理阻断"
                 :description="`任务：${preview.blockingTasks.join('、') || '无'}；代理：${preview.busyDemoAgents.join('、') || '无'}`" />
        <a-form layout="vertical" style="margin-top: 16px">
          <a-form-item :label="`输入确认短语：${preview.confirmationPhrase}`">
            <a-input v-model:value="phrase" :disabled="!preview.enabled" autocomplete="off" />
          </a-form-item>
          <a-form-item>
            <a-checkbox v-model:checked="acknowledged" :disabled="!preview.enabled">我已核对影响范围与当前阻断清单</a-checkbox>
          </a-form-item>
          <a-button danger :disabled="!canReset" :loading="restoring" @click="confirmRestore">恢复标准演示数据</a-button>
          <a-button style="margin-left: 8px" @click="loadPreview">刷新预览</a-button>
        </a-form>
      </template>
    </a-card>
    <a-alert v-if="result" type="success" show-icon style="margin-top: 16px"
             :message="`复位成功：${result.version}，耗时 ${result.durationMs} ms`"
             :description="`源摘要 ${result.sourceDigest}；业务数据摘要 ${result.contentDigest}`" />
  </div>
</template>

<script setup>
import { computed, onMounted, ref } from 'vue'
import { Modal, message } from 'ant-design-vue'
import request from '../../api/request'

const preview = ref(null)
const loading = ref(false)
const restoring = ref(false)
const phrase = ref('')
const acknowledged = ref(false)
const result = ref(null)
const canReset = computed(() => preview.value?.enabled && acknowledged.value
  && phrase.value === preview.value.confirmationPhrase
  && !preview.value.blockingTasks.length && !preview.value.busyDemoAgents.length)

async function loadPreview() {
  loading.value = true
  try {
    preview.value = (await request.get('/demo-data/reset-preview')).data
  } finally {
    loading.value = false
  }
}

function confirmRestore() {
  if (!canReset.value) return
  Modal.confirm({
    title: '再次确认恢复 F2 标准演示数据？',
    content: '六个仿真设备档案和能力画像、三套基线模板及三类任务定义将恢复到所示版本。',
    okText: '确认恢复',
    okType: 'danger',
    cancelText: '取消',
    onOk: restore
  })
}

async function restore() {
  restoring.value = true
  try {
    result.value = (await request.post('/demo-data/reset',
      { confirmationPhrase: phrase.value, confirmed: true })).data
    message.success('标准演示数据已恢复')
    phrase.value = ''
    acknowledged.value = false
    await loadPreview()
  } finally {
    restoring.value = false
  }
}

onMounted(loadPreview)
</script>
