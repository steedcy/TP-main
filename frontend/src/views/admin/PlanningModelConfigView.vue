<template>
  <div>
    <a-card title="规划模型 API 配置与手动切换" :loading="loading">
      <a-alert
        type="info"
        show-icon
        style="margin-bottom: 16px"
        message="主备任务规划模型路由与切换说明"
        description="支持「主备自动切换」「强制仅用第一模型」「强制仅用第二模型」三种模式。默认配置为「强制仅使用第二模型（gpt-sonnet-6.1）」。自动切换模式下默认使用第一模型（Kimi），仅当第一模型不可用（密钥未配置、连接超时、网络异常或 HTTP 非 200）时自动切换调用第二模型（gpt-sonnet-6.1）；内容不合规（1002）不切换。也可在下方手动指定当前使用的模型，保存后立即生效。"
      />

      <a-card type="inner" title="当前生效状态与最近一次调用监控" style="margin-bottom: 16px">
        <a-descriptions bordered :column="{ xs: 1, sm: 2 }" size="small">
          <a-descriptions-item label="当前生效调用模式">
            <a-tag :color="activeModeColor" data-testid="current-active-mode">
              {{ activeModeLabel }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="当前首选调用模型">
            <a-tag color="blue" data-testid="current-preferred-model">
              {{ currentPreferredModelText }}
            </a-tag>
          </a-descriptions-item>
          <a-descriptions-item label="最近一次实际命中模型">
            <template v-if="config.lastUsedSlot === 'PRIMARY'">
              <a-tag color="cyan" data-testid="last-used-model">第一模型：{{ config.lastUsedModel }}</a-tag>
            </template>
            <template v-else-if="config.lastUsedSlot === 'SECONDARY'">
              <a-tag color="purple" data-testid="last-used-model">第二模型：{{ config.lastUsedModel }}</a-tag>
            </template>
            <template v-else>
              <a-tag data-testid="last-used-model">尚无调用记录</a-tag>
            </template>
          </a-descriptions-item>
          <a-descriptions-item label="最近一次调用时间">
            <span data-testid="last-call-at">{{ config.lastCallAt || '—' }}</span>
          </a-descriptions-item>
          <a-descriptions-item label="最近一次调用结果详情" :span="2">
            <span data-testid="last-call-status">{{ config.lastCallStatus || '尚未发生模型调用' }}</span>
          </a-descriptions-item>
        </a-descriptions>
      </a-card>

      <a-form :model="form" layout="vertical" @finish="handleSave">
        <a-card type="inner" title="手动切换调用模式" style="margin-bottom: 16px">
          <a-form-item label="选择当前规划模型调用模式" name="activeMode" style="margin-bottom: 0">
            <a-radio-group v-model:value="form.activeMode" button-style="solid" data-testid="active-mode-group">
              <a-radio-button value="AUTO_FAILOVER">
                主备自动切换（推荐：优先第一模型 Kimi，不可用时自动切第二模型）
              </a-radio-button>
              <a-radio-button value="PRIMARY_ONLY">
                仅使用第一模型（强制 Kimi）
              </a-radio-button>
              <a-radio-button value="SECONDARY_ONLY">
                仅使用第二模型（强制直连 gpt-sonnet-6.1）
              </a-radio-button>
            </a-radio-group>
          </a-form-item>
        </a-card>

        <a-row :gutter="24">
          <a-col :xs="24" :lg="12">
            <a-card type="inner" title="第一模型（主模型：Kimi / Moonshot）">
              <a-descriptions bordered :column="1" size="small" style="margin-bottom: 16px">
                <a-descriptions-item label="当前密钥状态">
                  <a-tag :color="config.moonshotKeyConfigured ? 'green' : 'default'" data-testid="moonshot-key-status">
                    {{ config.moonshotKeyConfigured ? `已配置（${config.moonshotApiKeyMasked}）` : '未配置' }}
                  </a-tag>
                </a-descriptions-item>
              </a-descriptions>

              <a-form-item label="API 基础地址（HTTPS）" name="moonshotBaseUrl">
                <a-input
                  v-model:value="form.moonshotBaseUrl"
                  placeholder="https://api.moonshot.cn/v1"
                  data-testid="moonshot-base-url"
                />
              </a-form-item>

              <a-form-item label="模型名称" name="moonshotModel">
                <a-input
                  v-model:value="form.moonshotModel"
                  placeholder="kimi-k2.6"
                  data-testid="moonshot-model"
                />
              </a-form-item>

              <a-form-item
                label="API Key"
                name="moonshotApiKey"
                :extra="config.moonshotKeyConfigured ? '留空表示保持现有密钥不变；输入新密钥将覆盖保存' : '请输入 Kimi API Key'"
              >
                <a-input-password
                  v-model:value="form.moonshotApiKey"
                  placeholder="输入新的 Kimi API Key（留空保持不变）"
                  autocomplete="new-password"
                  data-testid="moonshot-api-key"
                />
              </a-form-item>

              <a-form-item v-if="config.moonshotKeyConfigured" name="clearMoonshotApiKey">
                <a-checkbox v-model:checked="form.clearMoonshotApiKey">
                  清除已保存的第一模型 API Key
                </a-checkbox>
              </a-form-item>
            </a-card>
          </a-col>

          <a-col :xs="24" :lg="12">
            <a-card type="inner" title="第二模型（默认主力模型：gpt-sonnet-6.1 / OpenAI 兼容中转）">
              <a-descriptions bordered :column="1" size="small" style="margin-bottom: 16px">
                <a-descriptions-item label="当前密钥状态">
                  <a-tag :color="config.claudeKeyConfigured ? 'green' : 'default'" data-testid="claude-key-status">
                    {{ config.claudeKeyConfigured ? `已配置（${config.claudeApiKeyMasked}）` : '未配置' }}
                  </a-tag>
                </a-descriptions-item>
              </a-descriptions>

              <a-form-item label="API 基础地址（HTTPS）" name="claudeBaseUrl">
                <a-input
                  v-model:value="form.claudeBaseUrl"
                  placeholder="https://ai.axuremart.com/v1"
                  data-testid="claude-base-url"
                />
              </a-form-item>

              <a-form-item label="模型名称" name="claudeModel">
                <a-input
                  v-model:value="form.claudeModel"
                  placeholder="gpt-sonnet-6.1"
                  data-testid="claude-model"
                />
              </a-form-item>

              <a-form-item
                label="API Key"
                name="claudeApiKey"
                :extra="config.claudeKeyConfigured ? '留空表示保持现有密钥不变；输入新密钥将覆盖保存' : '请输入第二模型 API Key'"
              >
                <a-input-password
                  v-model:value="form.claudeApiKey"
                  placeholder="输入新的第二模型 API Key（留空保持不变）"
                  autocomplete="new-password"
                  data-testid="claude-api-key"
                />
              </a-form-item>

              <a-form-item v-if="config.claudeKeyConfigured" name="clearClaudeApiKey">
                <a-checkbox v-model:checked="form.clearClaudeApiKey">
                  清除已保存的第二模型 API Key
                </a-checkbox>
              </a-form-item>
            </a-card>
          </a-col>
        </a-row>

        <div style="margin-top: 16px">
          <a-button type="primary" :loading="saving" @click="handleSave" data-testid="save-model-config">
            保存配置并应用模式
          </a-button>
          <a-button style="margin-left: 8px" @click="loadConfig" :disabled="saving">
            刷新状态
          </a-button>
        </div>
      </a-form>
    </a-card>
  </div>
</template>

<script setup>
import { computed, onMounted, reactive, ref } from 'vue'
import { message } from 'ant-design-vue'
import request from '../../api/request'

const loading = ref(false)
const saving = ref(false)

const config = reactive({
  moonshotBaseUrl: 'https://api.moonshot.cn/v1',
  moonshotModel: 'kimi-k2.6',
  moonshotKeyConfigured: false,
  moonshotApiKeyMasked: '',
  fallbackEnabled: false,
  activeMode: 'SECONDARY_ONLY',
  claudeBaseUrl: 'https://ai.axuremart.com/v1',
  claudeModel: 'gpt-sonnet-6.1',
  claudeKeyConfigured: false,
  claudeApiKeyMasked: '',
  lastUsedSlot: 'NONE',
  lastUsedModel: '',
  lastCallStatus: '尚未发生模型调用',
  lastCallAt: ''
})

const form = reactive({
  moonshotBaseUrl: 'https://api.moonshot.cn/v1',
  moonshotModel: 'kimi-k2.6',
  moonshotApiKey: '',
  clearMoonshotApiKey: false,
  activeMode: 'SECONDARY_ONLY',
  claudeBaseUrl: 'https://ai.axuremart.com/v1',
  claudeModel: 'gpt-sonnet-6.1',
  claudeApiKey: '',
  clearClaudeApiKey: false
})

const activeModeLabel = computed(() => {
  if (config.activeMode === 'SECONDARY_ONLY') return '强制仅使用第二模型'
  if (config.activeMode === 'AUTO_FAILOVER') return '主备自动切换（第一模型优先 -> 第二模型兜底）'
  return '仅使用第一模型'
})

const activeModeColor = computed(() => {
  if (config.activeMode === 'SECONDARY_ONLY') return 'purple'
  if (config.activeMode === 'AUTO_FAILOVER') return 'green'
  return 'blue'
})

const currentPreferredModelText = computed(() => {
  if (config.activeMode === 'SECONDARY_ONLY') {
    return `第二模型：${config.claudeModel}（${config.claudeBaseUrl}）`
  }
  if (config.activeMode === 'AUTO_FAILOVER') {
    return `第一模型：${config.moonshotModel}（不可用时自动切换第二模型：${config.claudeModel}）`
  }
  return `第一模型：${config.moonshotModel}（${config.moonshotBaseUrl}）`
})

function applyView(data) {
  if (!data) return
  Object.assign(config, data)
  form.moonshotBaseUrl = data.moonshotBaseUrl || 'https://api.moonshot.cn/v1'
  form.moonshotModel = data.moonshotModel || 'kimi-k2.6'
  form.moonshotApiKey = ''
  form.clearMoonshotApiKey = false
  form.activeMode = data.activeMode || (data.fallbackEnabled ? 'AUTO_FAILOVER' : 'SECONDARY_ONLY')
  form.claudeBaseUrl = data.claudeBaseUrl || 'https://ai.axuremart.com/v1'
  form.claudeModel = data.claudeModel || 'gpt-sonnet-6.1'
  form.claudeApiKey = ''
  form.clearClaudeApiKey = false
}

async function loadConfig() {
  loading.value = true
  try {
    const res = await request.get('/system-settings/planning-models')
    applyView(res.data)
  } finally {
    loading.value = false
  }
}

async function handleSave() {
  if (saving.value) return
  saving.value = true
  try {
    const payload = {
      moonshotBaseUrl: form.moonshotBaseUrl,
      moonshotModel: form.moonshotModel,
      moonshotApiKey: form.moonshotApiKey,
      clearMoonshotApiKey: form.clearMoonshotApiKey,
      fallbackEnabled: form.activeMode !== 'PRIMARY_ONLY',
      activeMode: form.activeMode,
      claudeBaseUrl: form.claudeBaseUrl,
      claudeModel: form.claudeModel,
      claudeApiKey: form.claudeApiKey,
      clearClaudeApiKey: form.clearClaudeApiKey
    }
    const res = await request.put('/system-settings/planning-models', payload)
    applyView(res.data)
    message.success('规划模型配置及调用模式已保存并生效')
  } finally {
    saving.value = false
  }
}

onMounted(loadConfig)
</script>
