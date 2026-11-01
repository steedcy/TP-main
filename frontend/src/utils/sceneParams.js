// 提交页按任务定义声明的场景参数动态渲染与校验（SRS_F010.R01、SRS_F022.R03，DEF-S3-028/029）。
// 预置任务族（含航班变更专用表单）不在此处渲染，缺失信息由提交后的追问流程补充；只处理扩展定义。

export function dynamicSceneFields(definition) {
  if (!definition || definition.isPreset) return []
  return (definition.sceneParams || []).map((p) => ({
    name: p.name,
    type: p.type || 'String',
    required: !!p.required,
    range: p.range || '',
    defaultValue: p.defaultValue ?? ''
  }))
}

export function initialSceneValues(fields) {
  const values = {}
  for (const f of fields) values[f.name] = f.defaultValue === '' ? undefined : f.defaultValue
  return values
}

function isBlank(v) {
  return v === undefined || v === null || (typeof v === 'string' && v.trim() === '')
}

// 返回 { ok, errors:[{name,message}] }，供提交按钮禁用与行内提示共用
export function validateSceneValues(fields, values) {
  const errors = []
  for (const f of fields) {
    const v = values[f.name]
    if (isBlank(v)) {
      if (f.required) errors.push({ name: f.name, message: `${f.name}为必填项` })
      continue
    }
    if (f.type === 'Integer' && !(Number.isInteger(Number(v)) && String(v).trim() !== '')) {
      errors.push({ name: f.name, message: `${f.name}须为整数` })
    } else if (f.type === 'Double' && !(Number.isFinite(Number(v)) && String(v).trim() !== '')) {
      errors.push({ name: f.name, message: `${f.name}须为数字` })
    } else if (f.type === 'Boolean' && typeof v !== 'boolean' && !['true', 'false'].includes(String(v))) {
      errors.push({ name: f.name, message: `${f.name}须为是/否` })
    } else if (f.type === 'String' && String(v).length > 500) {
      errors.push({ name: f.name, message: `${f.name}不得超过500字` })
    }
  }
  return { ok: errors.length === 0, errors }
}

// 生成提交给后端的 sceneParams：只带有值的字段，按声明类型转换
export function buildSceneParams(fields, values) {
  const out = {}
  for (const f of fields) {
    const v = values[f.name]
    if (isBlank(v)) continue
    if (f.type === 'Integer') out[f.name] = parseInt(v, 10)
    else if (f.type === 'Double') out[f.name] = Number(v)
    else if (f.type === 'Boolean') out[f.name] = typeof v === 'boolean' ? v : String(v) === 'true'
    else out[f.name] = String(v).trim()
  }
  return out
}
