// node src/utils/sceneParams.check.mjs  —— 无测试框架时的纯函数自检
import assert from 'node:assert/strict'
import { dynamicSceneFields, initialSceneValues, validateSceneValues, buildSceneParams } from './sceneParams.js'

const ext = { isPreset: false, sceneParams: [
  { name: 'sampleLocation', type: 'String', required: true },
  { name: 'headcount', type: 'Integer', required: false },
  { name: 'ratio', type: 'Double', required: false },
  { name: 'urgent', type: 'Boolean', required: false, defaultValue: 'false' } ] }
const fields = dynamicSceneFields(ext)
assert.equal(fields.length, 4)
assert.deepEqual(dynamicSceneFields({ isPreset: true, sceneParams: ext.sceneParams }), [], '预置不渲染')
assert.deepEqual(dynamicSceneFields(null), [])
assert.deepEqual(dynamicSceneFields({ isPreset: false }), [])

assert.equal(initialSceneValues(fields).urgent, 'false')
assert.equal(initialSceneValues(fields).sampleLocation, undefined)

let r = validateSceneValues(fields, {})
assert.equal(r.ok, false); assert.equal(r.errors[0].name, 'sampleLocation')
assert.equal(validateSceneValues(fields, { sampleLocation: '   ' }).ok, false)
assert.equal(validateSceneValues(fields, { sampleLocation: 'F2' }).ok, true)
assert.equal(validateSceneValues(fields, { sampleLocation: 'F2', headcount: '3' }).ok, true)
assert.equal(validateSceneValues(fields, { sampleLocation: 'F2', headcount: '2.5' }).ok, false)
assert.equal(validateSceneValues(fields, { sampleLocation: 'F2', headcount: 'abc' }).ok, false)
assert.equal(validateSceneValues(fields, { sampleLocation: 'F2', ratio: 'x' }).ok, false)
assert.equal(validateSceneValues(fields, { sampleLocation: 'F2', ratio: '0.5' }).ok, true)
assert.equal(validateSceneValues(fields, { sampleLocation: 'F2', urgent: 'maybe' }).ok, false)
assert.equal(validateSceneValues(fields, { sampleLocation: 'x'.repeat(501) }).ok, false)

assert.deepEqual(buildSceneParams(fields, { sampleLocation: ' F2 ', headcount: '3', ratio: '0.5', urgent: 'true' }),
  { sampleLocation: 'F2', headcount: 3, ratio: 0.5, urgent: true })
assert.deepEqual(buildSceneParams(fields, { sampleLocation: 'F2' }), { sampleLocation: 'F2' })
console.log('sceneParams checks passed')
