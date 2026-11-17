<template>
  <section class="task-board">
    <header class="board-header">
      <div>
        <h2>任务协同看板</h2>
        <p>F2 航站楼空间态势 · 规划/风险/调度全链路实况、历史回溯与人工空间规划</p>
      </div>
      <a-space wrap>
        <a-radio-group v-model:value="mode" button-style="solid" size="small">
          <a-radio-button value="live">实况监控</a-radio-button>
          <a-radio-button value="playback">历史回溯</a-radio-button>
        </a-radio-group>
        <a-select
          v-model:value="selectedTaskId"
          style="width: 320px"
          show-search
          :filter-option="filterTaskOption"
          placeholder="选择要查看的任务"
          @change="handleSelectTask"
        >
          <a-select-option v-for="t in taskList" :key="t.id" :value="t.id">
            #{{ t.id }} · {{ t.taskCode }} · {{ statusLabel(t.status) }}
          </a-select-option>
        </a-select>
        <a-button v-if="isOperator" @click="spaceDrawerOpen = true">空间 POI 与区域管理</a-button>
        <a-button v-if="isOperator" type="primary" @click="quickModalOpen = true">发起位置感知任务</a-button>
        <a-button :loading="loading" @click="refreshAll">刷新</a-button>
      </a-space>
    </header>

    <!-- 绘制模式提示条 -->
    <a-alert
      v-if="drawMode"
      type="info"
      show-icon
      style="margin-bottom: 12px"
      :message="drawBannerTitle"
    >
      <template #action>
        <a-space>
          <a-button v-if="drawMode === 'ISOLATED_ZONE' || drawMode === 'CHECKIN_HALL' || drawMode === 'CORRIDOR'" size="small" type="primary" @click="finishDrawing">
            完成绘制（已选 {{ drawPoints.length }} 点）
          </a-button>
          <a-button size="small" @click="cancelDrawing">取消</a-button>
        </a-space>
      </template>
    </a-alert>

    <a-row :gutter="16">
      <!-- 左侧：F2 互动平面图 + POI + 隔离区/走廊 + 实时路线引导 -->
      <a-col :xs="24" :lg="14">
        <a-card class="map-card" :body-style="{ padding: '12px' }">
          <div class="map-toolbar">
            <a-space wrap size="small">
              <a-button size="small" @click="zoomBy(1.25)">＋</a-button>
              <a-button size="small" @click="zoomBy(0.8)">－</a-button>
              <a-button size="small" @click="focusActiveArea">聚焦活动区</a-button>
              <a-button size="small" @click="fitAll">全图</a-button>
              <a-tag color="blue">{{ Math.round(zoom * 100) }}%</a-tag>
              <a-button
                size="small"
                :type="drawMode === 'PASSENGER' ? 'primary' : 'default'"
                @click="togglePickPassenger"
              >
                {{ drawMode === 'PASSENGER' ? '点击地图定位旅客中…' : '地图点选旅客位置' }}
              </a-button>
              <template v-if="isOperator">
                <a-button size="small" @click="startDrawRegion('CHECKIN_HALL')">绘制值机办理区</a-button>
                <a-button size="small" @click="startDrawRegion('ISOLATED_ZONE')">绘制候机隔离区</a-button>
                <a-button size="small" @click="startDrawRegion('CORRIDOR')">绘制走廊</a-button>
              </template>
            </a-space>
            <a-space wrap size="small" style="margin-top: 6px;">
              <span style="font-size: 12px; color: #666;">图层：</span>
              <a-checkbox v-model:checked="showPois">POI 点位（{{ pois.length }}）</a-checkbox>
              <a-checkbox v-model:checked="showRegions">功能区域/走廊（{{ regions.length }}）</a-checkbox>
              <a-checkbox v-model:checked="showRoute">路线引导图</a-checkbox>
              <a-checkbox v-model:checked="showCollabLinks">设备协同连线</a-checkbox>
              <span v-if="routeInfo.totalPixels > 0" class="route-badge">
                引导路径约 {{ routeInfo.totalPixels }} 像素（{{ routeStopNames.join(' → ') }}）
              </span>
            </a-space>
          </div>

          <div
            ref="viewportRef"
            class="map-viewport"
            :class="{ picking: Boolean(drawMode) }"
            @wheel.prevent="handleWheel"
            @pointerdown="startPan"
            @pointermove="movePan"
            @pointerup="endPan"
            @pointercancel="endPan"
          >
            <div class="map-canvas" :style="canvasStyle" @click="handleMapClick">
              <img class="floorplan" src="/F2.jpg" alt="F2 平面图" draggable="false" />

              <!-- SVG 隔离区、走廊、路径引导与设备协同连线层 -->
              <svg class="map-svg" :viewBox="`0 0 ${MAP_WIDTH} ${MAP_HEIGHT}`">
                <!-- 已保存的值机办理区、候机隔离区与走廊 -->
                <g v-if="showRegions">
                  <template v-for="reg in parsedRegions" :key="reg.id">
                    <polygon
                      v-if="reg.regionType === 'ISOLATED_ZONE' && reg.points.length >= 3"
                      :points="reg.points.map(p => `${p.x},${p.y}`).join(' ')"
                      fill="rgba(114, 46, 209, 0.14)"
                      stroke="#722ed1"
                      stroke-width="3"
                      stroke-dasharray="8 6"
                    />
                    <polygon
                      v-else-if="reg.regionType === 'CHECKIN_HALL' && reg.points.length >= 3"
                      :points="reg.points.map(p => `${p.x},${p.y}`).join(' ')"
                      fill="rgba(82, 196, 26, 0.14)"
                      stroke="#389e0d"
                      stroke-width="3"
                      stroke-dasharray="8 6"
                    />
                    <polyline
                      v-else-if="reg.regionType === 'CORRIDOR' && reg.points.length >= 2"
                      :points="reg.points.map(p => `${p.x},${p.y}`).join(' ')"
                      fill="none"
                      stroke="#13c2c2"
                      stroke-width="10"
                      stroke-linecap="round"
                      stroke-linejoin="round"
                      opacity="0.45"
                    />
                    <text
                      v-if="reg.points.length"
                      :x="reg.points[0].x"
                      :y="reg.points[0].y - 10"
                      :fill="reg.regionType === 'ISOLATED_ZONE' ? '#531dab' : reg.regionType === 'CHECKIN_HALL' ? '#237804' : '#08979c'"
                      font-size="14"
                      font-weight="bold"
                    >
                      {{ reg.regionType === 'ISOLATED_ZONE' ? '候机隔离区：' : reg.regionType === 'CHECKIN_HALL' ? '值机办理区：' : '走廊通道：' }}{{ reg.regionName }}
                    </text>
                  </template>
                </g>

                <!-- 正在绘制中的预览 -->
                <g v-if="(drawMode === 'ISOLATED_ZONE' || drawMode === 'CHECKIN_HALL' || drawMode === 'CORRIDOR') && drawPoints.length">
                  <polyline
                    :points="drawPoints.map(p => `${p.x},${p.y}`).join(' ')"
                    fill="none"
                    :stroke="drawMode === 'ISOLATED_ZONE' ? '#722ed1' : drawMode === 'CHECKIN_HALL' ? '#389e0d' : '#13c2c2'"
                    stroke-width="5"
                    stroke-dasharray="6 4"
                  />
                  <circle
                    v-for="(pt, idx) in drawPoints"
                    :key="`dp-${idx}`"
                    :cx="pt.x"
                    :cy="pt.y"
                    r="8"
                    :fill="drawMode === 'ISOLATED_ZONE' ? '#722ed1' : drawMode === 'CHECKIN_HALL' ? '#389e0d' : '#13c2c2'"
                    stroke="#fff"
                    stroke-width="2"
                  />
                </g>

                <!-- 设备协同连线 -->
                <g v-if="showCollabLinks && collabEdges.length">
                  <line
                    v-for="(edge, idx) in collabEdges"
                    :key="`collab-${idx}`"
                    :x1="edge.x1"
                    :y1="edge.y1"
                    :x2="edge.x2"
                    :y2="edge.y2"
                    stroke="#fa8c16"
                    stroke-width="4"
                    stroke-dasharray="10 8"
                    opacity="0.75"
                  />
                </g>

                <!-- 实时走廊路线引导图 -->
                <g v-if="showRoute && routeInfo.points.length >= 2">
                  <polyline
                    :points="routePolylinePoints"
                    fill="none"
                    stroke="#1677ff"
                    stroke-width="8"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                    opacity="0.25"
                  />
                  <polyline
                    class="route-animated"
                    :points="routePolylinePoints"
                    fill="none"
                    stroke="#1677ff"
                    stroke-width="5"
                    stroke-dasharray="16 10"
                    stroke-linecap="round"
                    stroke-linejoin="round"
                  />
                  <g v-for="(pt, idx) in routeStopPoints" :key="`stop-${idx}`">
                    <circle :cx="pt.x" :cy="pt.y" r="14" fill="#1677ff" stroke="#fff" stroke-width="3" />
                    <text :x="pt.x" :y="pt.y + 5" text-anchor="middle" fill="#fff" font-size="13" font-weight="bold">
                      {{ idx + 1 }}
                    </text>
                  </g>
                </g>
              </svg>

              <!-- 预设 / 人工管理 POI 点位 -->
              <template v-if="showPois">
                <div
                  v-for="poi in pois"
                  :key="poi.poiCode"
                  class="poi-marker"
                  :style="{ left: `${poi.x}px`, top: `${poi.y}px`, '--poi-color': poiColor(poi.category) }"
                  :title="`${poi.poiName} (${poi.x}, ${poi.y})`"
                  @click.stop="handlePoiClick(poi)"
                >
                  <span class="poi-dot">{{ poiBadge(poi.category) }}</span>
                  <span class="poi-label">{{ poi.poiName }}</span>
                </div>
              </template>

              <!-- 旅客当前位置 -->
              <div
                v-if="effectivePassengerPoint"
                class="passenger-marker"
                :style="{ left: `${effectivePassengerPoint.x}px`, top: `${effectivePassengerPoint.y}px` }"
              >
                <span class="passenger-pulse"></span>
                <span class="passenger-icon">🧑</span>
                <span class="passenger-label">旅客位置：{{ effectivePassengerPoint.label }}</span>
              </div>

              <!-- 7 台实时设备 -->
              <div
                v-for="device in positionedDevices"
                :key="device.deviceCode"
                class="device-marker"
                :class="deviceMarkerClass(device)"
                :style="{ left: `${device.location.x}px`, top: `${device.location.y}px` }"
                :title="`${device.deviceName} (${device.deviceCode})`"
              >
                <span class="device-dot"></span>
                <span class="device-label">
                  {{ device.deviceName }}
                  <template v-if="activeDeviceStepMap[device.agentId]">
                    · 执行第{{ activeDeviceStepMap[device.agentId] }}步
                  </template>
                </span>
              </div>
            </div>
          </div>
          <div class="map-footer">
            <span>指针坐标：{{ cursorPos ? `X ${cursorPos.x}, Y ${cursorPos.y}` : '—' }}</span>
            <span>支持滚轮缩放、左键拖拽平移；运行操作员可在右侧打开“空间 POI 与区域管理”自定义点位</span>
          </div>
        </a-card>
      </a-col>

      <!-- 右侧：全链路决策流水线 + 回放控制 + 设备实时气泡视窗 -->
      <a-col :xs="24" :lg="10">
        <a-card size="small" style="margin-bottom: 12px">
          <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
            <div>
              <strong>{{ currentTask?.taskCode || '未选择任务' }}</strong>
              <a-tag v-if="currentTask" :color="statusColor(currentTask.status)" style="margin-left: 8px">
                {{ statusLabel(currentTask.status) }}
              </a-tag>
              <a-tag v-if="mode === 'live' && isRunning(currentTask?.status)" color="processing">每 2 秒自动刷新</a-tag>
            </div>
            <a-space size="small">
              <a-button size="small" type="primary" @click="togglePlayback">
                {{ playbackPlaying ? '⏸ 暂停回放' : '▶ 过程回放' }}
              </a-button>
              <a-button size="small" @click="resetPlayback">重置</a-button>
              <a-select v-model:value="playbackSpeed" size="small" style="width: 72px">
                <a-select-option :value="1">1倍速</a-select-option>
                <a-select-option :value="2">2倍速</a-select-option>
              </a-select>
            </a-space>
          </div>
          <div v-if="currentTask" style="margin-top: 8px; font-size: 12px; color: #555;">
            <b>任务目标：</b>{{ currentTask.taskGoal }}
          </div>
          <a-progress
            style="margin-top: 8px"
            :percent="stagePercent"
            :status="currentTask?.status === 'FAILED' ? 'exception' : stagePercent === 100 ? 'success' : 'active'"
            size="small"
          />
        </a-card>

        <a-card title="全链路规划与调度实况" size="small" style="margin-bottom: 12px">
          <a-steps direction="vertical" size="small" :current="visibleStageIndex">
            <a-step title="1. 目标理解与空间定位" :status="stageStatus(0)">
              <template #description>
                <div class="stage-desc">
                  <span>业务场景：<b>{{ translateTaskFamily(currentTask?.taskFamily) }}</b></span>
                  <span v-if="effectivePassengerPoint"> · 起点：{{ effectivePassengerPoint.label }}</span>
                  <span v-if="effectiveViaPoint"> · 途经：{{ effectiveViaPoint.label }}</span>
                  <span v-if="effectiveDestPoint"> · 目标：{{ effectiveDestPoint.label }}</span>
                </div>
              </template>
            </a-step>
            <a-step title="2. 规划上下文设备快照" :status="stageStatus(1)">
              <template #description>
                <div class="stage-desc">
                  可用资源快照：<b>{{ snapshotSummary }}</b>
                </div>
              </template>
            </a-step>
            <a-step title="3. 模型候选规划与三类校验" :status="stageStatus(2)">
              <template #description>
                <div class="stage-desc">
                  <template v-if="latestModelPlan">
                    模型生成方案第 {{ latestModelPlan.versionNo }} 版（共 {{ latestModelPlan.planSteps?.length || 0 }} 个步骤）·
                    校验结果：<a-tag :color="latestModelPlan.validationStatus === 'PASSED' ? 'green' : 'red'">
                      {{ latestModelPlan.validationStatus === 'PASSED' ? '校验通过' : '校验拦截' }}
                    </a-tag>
                  </template>
                  <template v-else>尚未生成模型候选计划</template>
                </div>
              </template>
            </a-step>
            <a-step title="4. 监督风险判定与基线降级" :status="stageStatus(3)">
              <template #description>
                <div class="stage-desc">
                  <template v-if="activePlan">
                    当前生效方案：第 {{ activePlan.versionNo }} 版（{{ activePlan.planSource === 'BASELINE_TEMPLATE' ? '基线模板降级' : '自主规划执行' }}）·
                    风险等级：<a-tag :color="activePlan.riskLevel === 'HIGH' ? 'red' : 'green'">
                      {{ activePlan.riskLevel === 'HIGH' ? '高风险' : '低风险' }}
                    </a-tag>
                    <div v-if="currentTask?.downgradeReason" style="color: #cf1322; margin-top: 2px;">
                      降级说明：{{ currentTask.downgradeReason }}
                    </div>
                  </template>
                  <template v-else>等待监督智能体判定</template>
                </div>
              </template>
            </a-step>
            <a-step title="5. 动态设备选型与协同执行" :status="stageStatus(4)">
              <template #description>
                <div class="stage-desc">
                  <div v-for="s in visibleSteps" :key="s.stepSeq" class="step-pill">
                    <span>第 {{ s.stepSeq }} 步：{{ capabilityLabel(s.capabilityType) }}</span>
                    <a-tag :color="stepTagColor(s.stepStatus)">{{ translateStepStatus(s.stepStatus) }}</a-tag>
                    <span style="color: #666;">执行设备：{{ s.deviceName || '未分配' }}</span>
                  </div>
                  <div v-if="!visibleSteps.length" style="color: #999;">尚未进入设备分派阶段</div>
                </div>
              </template>
            </a-step>
          </a-steps>
        </a-card>

        <a-card title="设备实时展示与执行气泡" size="small">
          <div v-if="!deviceBubbles.length" style="color: #999; font-size: 12px;">
            当前阶段暂无设备指令输出，提交任务或点击“过程回放”查看。
          </div>
          <div class="bubble-list">
            <div v-for="b in deviceBubbles" :key="`${b.stepSeq}-${b.agentCode}`" class="bubble-item">
              <div class="bubble-avatar">{{ b.icon }}</div>
              <div class="bubble-content">
                <div class="bubble-header">
                  <strong>{{ b.deviceLabel }}</strong>
                  <a-tag :color="stepTagColor(b.status)" size="small">{{ translateStepStatus(b.status) }}</a-tag>
                </div>
                <div class="bubble-text">
                  <div v-if="b.commandText"><b>下发指令：</b>{{ b.commandText }}</div>
                  <div v-if="b.feedbackText" style="color: #389e0d; margin-top: 2px;"><b>设备回执：</b>{{ b.feedbackText }}</div>
                </div>
              </div>
            </div>
          </div>
        </a-card>
      </a-col>
    </a-row>

    <!-- 空间 POI 与区域管理抽屉（仅运行操作员） -->
    <a-drawer v-model:open="spaceDrawerOpen" title="空间 POI 与隔离区/走廊管理" width="560">
      <a-tabs>
        <a-tab-pane key="pois" tab="POI 点位管理">
          <div style="display: flex; justify-content: space-between; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
            <a-space>
              <a-button type="primary" size="small" @click="openPoiModal(null)">新增 POI</a-button>
              <a-button size="small" :loading="syncingScanners" @click="handleSyncScanners">同步行李测量仿真体坐标</a-button>
            </a-space>
            <a-select v-model:value="poiCategoryFilter" size="small" style="width: 150px" allow-clear placeholder="按类型筛选">
              <a-select-option v-for="c in POI_CATEGORIES" :key="c.key" :value="c.key">{{ c.label }}</a-select-option>
            </a-select>
          </div>
          <a-table :data-source="filteredPois" :pagination="{ pageSize: 8 }" size="small" row-key="poiCode">
            <a-table-column title="名称" data-index="poiName" key="poiName" />
            <a-table-column title="类型" key="category">
              <template #default="{ record }">
                <a-tag :color="poiColor(record.category)">{{ poiCategoryLabel(record.category) }}</a-tag>
              </template>
            </a-table-column>
            <a-table-column title="坐标 (X, Y)" key="coords">
              <template #default="{ record }">{{ Math.round(record.x) }}, {{ Math.round(record.y) }}</template>
            </a-table-column>
            <a-table-column title="操作" key="actions" width="120">
              <template #default="{ record }">
                <a-space size="small">
                  <a-button type="link" size="small" style="padding: 0" @click="openPoiModal(record)">编辑</a-button>
                  <a-popconfirm v-if="record.id" title="确认删除该 POI？" @confirm="handleDeletePoi(record.id)">
                    <a-button type="link" size="small" danger style="padding: 0">删除</a-button>
                  </a-popconfirm>
                </a-space>
              </template>
            </a-table-column>
          </a-table>
        </a-tab-pane>

        <a-tab-pane key="regions" tab="功能区域与走廊规划">
          <div style="margin-bottom: 12px;">
            <a-space wrap>
              <a-button size="small" @click="spaceDrawerOpen = false; startDrawRegion('CHECKIN_HALL')">
                绘制值机办理区
              </a-button>
              <a-button type="primary" size="small" @click="spaceDrawerOpen = false; startDrawRegion('ISOLATED_ZONE')">
                绘制候机隔离区
              </a-button>
              <a-button size="small" @click="spaceDrawerOpen = false; startDrawRegion('CORRIDOR')">
                绘制通行走廊
              </a-button>
            </a-space>
            <p style="font-size: 12px; color: #666; margin-top: 6px;">
              值机办理区为安检前值机/行李托运区；候机隔离区为过安检后连通各登机口的区域；绘制走廊后，系统将沿隔离区与大厅内走廊计算引导路线。
            </p>
          </div>
          <a-table :data-source="regions" :pagination="false" size="small" row-key="id">
            <a-table-column title="区域名称" data-index="regionName" key="regionName" />
            <a-table-column title="类型" key="regionType">
              <template #default="{ record }">
                <a-tag :color="record.regionType === 'ISOLATED_ZONE' ? 'purple' : record.regionType === 'CHECKIN_HALL' ? 'green' : 'cyan'">
                  {{ record.regionType === 'ISOLATED_ZONE' ? '安检后候机隔离区' : record.regionType === 'CHECKIN_HALL' ? '值机办理区' : '通行走廊' }}
                </a-tag>
              </template>
            </a-table-column>
            <a-table-column title="操作" key="actions" width="80">
              <template #default="{ record }">
                <a-popconfirm title="确认删除该区域？" @confirm="handleDeleteRegion(record.id)">
                  <a-button type="link" size="small" danger style="padding: 0">删除</a-button>
                </a-popconfirm>
              </template>
            </a-table-column>
          </a-table>
        </a-tab-pane>
      </a-tabs>
    </a-drawer>

    <!-- 新增/编辑 POI 弹窗 -->
    <a-modal v-model:open="poiModalOpen" :title="poiForm.id ? '编辑 POI 点位' : '新增 POI 点位'" @ok="handleSavePoi">
      <a-form layout="vertical">
        <a-form-item label="POI 编码（唯一标识）">
          <a-input v-model:value="poiForm.poiCode" :disabled="Boolean(poiForm.id)" placeholder="例如 GATE_A08 或 安检通道03" />
        </a-form-item>
        <a-form-item label="POI 中文名称">
          <a-input v-model:value="poiForm.poiName" placeholder="例如 登机口 A08" />
        </a-form-item>
        <a-form-item label="POI 类型">
          <a-select v-model:value="poiForm.category" @change="handlePoiCategoryChange">
            <a-select-option v-for="c in POI_CATEGORIES" :key="c.key" :value="c.key">{{ c.label }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="poiForm.category === 'MEASURE'" label="关联行李测量仿真体（选择后自动填入其坐标）">
          <a-select v-model:value="poiForm.linkedDeviceCode" allow-clear @change="handleScannerDeviceSelect">
            <a-select-option v-for="d in scannerDevices" :key="d.deviceCode" :value="d.deviceCode">
              {{ d.deviceName }} ({{ d.deviceCode }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-row :gutter="12">
          <a-col :span="10">
            <a-form-item label="X 坐标（像素）"><a-input-number v-model:value="poiForm.x" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="10">
            <a-form-item label="Y 坐标（像素）"><a-input-number v-model:value="poiForm.y" style="width: 100%" /></a-form-item>
          </a-col>
          <a-col :span="4" style="display: flex; align-items: flex-end; padding-bottom: 24px;">
            <a-button size="small" @click="startPickPoiCoord">地图拾取</a-button>
          </a-col>
        </a-row>
        <a-form-item label="所属区域（可选）">
          <a-input v-model:value="poiForm.zone" placeholder="如 A指廊 / 中央安检区" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 保存区域命名弹窗 -->
    <a-modal v-model:open="regionNameModalOpen" title="保存绘制区域" @ok="handleSaveRegion">
      <a-form layout="vertical">
        <a-form-item label="区域名称">
          <a-input v-model:value="regionNameInput" placeholder="如：T2施工隔离区 / 中央主走廊" />
        </a-form-item>
      </a-form>
    </a-modal>

    <!-- 发起位置感知任务弹窗 -->
    <a-modal
      v-model:open="quickModalOpen"
      title="发起空间协同演示任务"
      :confirm-loading="quickSubmitting"
      @ok="handleQuickSubmit"
    >
      <a-form layout="vertical">
        <a-form-item label="任务场景">
          <a-select v-model:value="quickForm.scenario">
            <a-select-option value="SPECIAL_PASSENGER_SERVICE">特殊旅客协同服务（支持经安检至登机口）</a-select-option>
            <a-select-option value="FLIGHT_CHANGE_RESPONSE">航班变更发布与多渠道引导</a-select-option>
            <a-select-option value="OVERSIZE_BAGGAGE_HANDLING">行李测量与超规专柜引导</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="旅客 / 事发当前位置（也可先在地图点选）">
          <a-select v-model:value="quickForm.origin" show-search>
            <a-select-option v-for="p in pois" :key="p.poiCode" :value="p.poiCode">
              {{ p.poiName }} ({{ Math.round(p.x) }}, {{ Math.round(p.y) }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="quickForm.scenario === 'SPECIAL_PASSENGER_SERVICE'" label="途经安检通道（用于路线引导图，可选）">
          <a-select v-model:value="quickForm.viaSecurity" allow-clear placeholder="不选则直达目的地">
            <a-select-option v-for="p in securityPois" :key="p.poiCode" :value="p.poiCode">{{ p.poiName }}</a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item label="目标登机口 / 专柜">
          <a-select v-model:value="quickForm.destination" show-search>
            <a-select-option v-for="p in destPois" :key="p.poiCode" :value="p.poiCode">
              {{ p.poiName }} ({{ Math.round(p.x) }}, {{ Math.round(p.y) }})
            </a-select-option>
          </a-select>
        </a-form-item>
        <a-form-item v-if="quickForm.scenario === 'SPECIAL_PASSENGER_SERVICE'" label="协助类型">
          <a-select v-model:value="quickForm.assistanceType">
            <a-select-option value="轮椅陪同">轮椅陪同</a-select-option>
            <a-select-option value="视障引导">视障引导</a-select-option>
            <a-select-option value="无陪儿童">无陪儿童</a-select-option>
          </a-select>
        </a-form-item>
      </a-form>
    </a-modal>
  </section>
</template>

<script setup>
import { computed, onBeforeUnmount, onMounted, reactive, ref, watch } from 'vue'
import { useRoute } from 'vue-router'
import { message } from 'ant-design-vue'
import { useAuthStore } from '../../store/auth'
import request from '../../api/request'
import {
  createMapRegion,
  createPoi,
  deleteMapRegion,
  deletePoi,
  getContextSnapshots,
  getMapLayout,
  getPlanVersions,
  getStepAssignments,
  getTask,
  getTaskBoardCommands,
  getTaskEvents,
  listTasks,
  submitTask,
  syncScannerPois,
  updatePoi
} from '../../api/task'
import {
  DEFAULT_TERMINAL_POIS,
  MAP_HEIGHT,
  MAP_WIDTH,
  POI_CATEGORIES,
  computeTerminalRoute,
  formatReadableCommand,
  formatReadableFeedback,
  nearestPoi,
  parseRegionGeometry,
  resolveLocation,
  translateStepStatus,
  translateTaskFamily
} from '../../utils/terminalMap'

const route = useRoute()
const authStore = useAuthStore()
const isOperator = computed(() => authStore.role === 'OPERATOR')

const mode = ref('live')
const loading = ref(false)
const taskList = ref([])
const selectedTaskId = ref(null)
const currentTask = ref(null)
const planVersions = ref([])
const contextSnapshots = ref([])
const stepAssignments = ref([])
const taskEvents = ref([])
const taskCommands = ref([])
const devices = ref([])

const pois = ref([...DEFAULT_TERMINAL_POIS])
const regions = ref([])

// 地图交互状态
const viewportRef = ref(null)
const zoom = ref(0.65)
const pan = reactive({ x: 0, y: -1750 })
const dragging = ref(false)
const dragOrigin = reactive({ x: 0, y: 0, panX: 0, panY: 0 })
const cursorPos = ref(null)
const manualPassengerPoint = ref(null)

// 空间绘制 / 拾取模式: null | 'PASSENGER' | 'POI_PICK' | 'ISOLATED_ZONE' | 'CORRIDOR'
const drawMode = ref(null)
const drawPoints = ref([])
const regionNameModalOpen = ref(false)
const regionNameInput = ref('')

// POI 与区域管理抽屉
const spaceDrawerOpen = ref(false)
const poiCategoryFilter = ref(undefined)
const syncingScanners = ref(false)
const poiModalOpen = ref(false)
const poiForm = reactive({
  id: null,
  poiCode: '',
  poiName: '',
  category: 'GATE',
  x: 600,
  y: 4200,
  zone: '',
  linkedDeviceCode: null
})

const showPois = ref(true)
const showRegions = ref(true)
const showRoute = ref(true)
const showCollabLinks = ref(true)

// 回放状态
const playbackPlaying = ref(false)
const playbackSpeed = ref(1)
const playbackStep = ref(5)
let liveTimer = null
let playbackTimer = null

// 快捷发起弹窗
const quickModalOpen = ref(false)
const quickSubmitting = ref(false)
const quickForm = reactive({
  scenario: 'SPECIAL_PASSENGER_SERVICE',
  origin: 'T2值机区',
  viaSecurity: 'VIP安检通道',
  destination: 'GATE_A05',
  assistanceType: '轮椅陪同'
})

const drawBannerTitle = computed(() => {
  if (drawMode.value === 'PASSENGER') return '请直接在地图上点击旅客当前所在位置'
  if (drawMode.value === 'POI_PICK') return '请直接在地图上点击该 POI 的目标位置'
  if (drawMode.value === 'CHECKIN_HALL') return '请依次点击值机办理区顶点（至少 3 个点），然后点击右侧“完成绘制”'
  if (drawMode.value === 'ISOLATED_ZONE') return '请依次点击安检后候机隔离区顶点（至少 3 个点），然后点击右侧“完成绘制”'
  if (drawMode.value === 'CORRIDOR') return '请依次点击贯穿各登机口的走廊路径节点（至少 2 个点），然后点击右侧“完成绘制”'
  return ''
})

const parsedRegions = computed(() =>
  regions.value.map(r => ({ ...r, points: parseRegionGeometry(r) }))
)

const filteredPois = computed(() =>
  poiCategoryFilter.value ? pois.value.filter(p => p.category === poiCategoryFilter.value) : pois.value
)

const scannerDevices = computed(() =>
  devices.value.filter(d => (d.simulatedDeviceType || d.deviceTypeCode) === 'BAGGAGE_SCANNER')
)

const securityPois = computed(() => pois.value.filter(p => p.category === 'SECURITY'))
const destPois = computed(() =>
  pois.value.filter(p => ['GATE', 'BAGGAGE', 'SHOP', 'FACILITY', 'SERVICE'].includes(p.category))
)

const canvasStyle = computed(() => ({
  width: `${MAP_WIDTH}px`,
  height: `${MAP_HEIGHT}px`,
  transform: `translate(${pan.x}px, ${pan.y}px) scale(${zoom.value})`,
  transformOrigin: '0 0'
}))

const positionedDevices = computed(() =>
  devices.value.filter(d => d.location && Number.isFinite(Number(d.location.x)) && Number.isFinite(Number(d.location.y)))
)

const sceneParamsObj = computed(() => {
  const raw = currentTask.value?.sceneParams
  if (!raw) return {}
  if (typeof raw === 'string') {
    try { return JSON.parse(raw) } catch { return {} }
  }
  return raw
})

const effectivePassengerPoint = computed(() => {
  if (manualPassengerPoint.value) return manualPassengerPoint.value
  const sp = sceneParamsObj.value
  const parsed = currentTask.value?.goalParsingResult || {}
  const cand = sp.origin || sp.baggageLocation || parsed.origin
  return resolveLocation(cand, pois.value, devices.value) || resolveLocation('T2值机区', pois.value, devices.value)
})

const effectiveViaPoint = computed(() => {
  const via = sceneParamsObj.value.viaSecurity || (mode.value === 'live' && quickForm.viaSecurity)
  return via ? resolveLocation(via, pois.value, devices.value) : null
})

const effectiveDestPoint = computed(() => {
  const sp = sceneParamsObj.value
  const parsed = currentTask.value?.goalParsingResult || {}
  const cand = sp.destination || sp.targetCounter || sp.newGate || parsed.destination
  return resolveLocation(cand, pois.value, devices.value) || resolveLocation('GATE_A05', pois.value, devices.value)
})

const routeInfo = computed(() => {
  const stops = [effectivePassengerPoint.value, effectiveViaPoint.value, effectiveDestPoint.value].filter(Boolean)
  return computeTerminalRoute(stops, regions.value)
})

const routePolylinePoints = computed(() =>
  routeInfo.value.points.map(p => `${p.x},${p.y}`).join(' ')
)

const routeStopPoints = computed(() =>
  [effectivePassengerPoint.value, effectiveViaPoint.value, effectiveDestPoint.value].filter(Boolean)
)

const routeStopNames = computed(() => routeStopPoints.value.map(p => p.label || '点位'))

const visibleStageIndex = computed(() => {
  if (mode.value === 'playback') return playbackStep.value
  if (!currentTask.value) return 0
  if (stepAssignments.value.length) return 4
  if (planVersions.value.length) return 3
  if (contextSnapshots.value.length) return 1
  return 0
})

const stagePercent = computed(() => Math.min(100, Math.round((visibleStageIndex.value / 4) * 100)))

const latestModelPlan = computed(() =>
  [...planVersions.value].reverse().find(p => p.planSource !== 'BASELINE_TEMPLATE') || null
)

const activePlan = computed(() => {
  const id = currentTask.value?.currentPlanVersionId
  return planVersions.value.find(p => p.id === id) || planVersions.value[planVersions.value.length - 1] || null
})

const snapshotSummary = computed(() => {
  const snap = contextSnapshots.value[contextSnapshots.value.length - 1]
  if (!snap) return `当前在线设备 ${devices.value.filter(d => d.onlineStatus === 'ONLINE').length} 台`
  return `上下文快照 #${snap.id}（已采集中枢与设备实时状态）`
})

const mergedSteps = computed(() => {
  const planSteps = activePlan.value?.planSteps || []
  const cmdMap = new Map()
  for (const c of taskCommands.value) cmdMap.set(c.stepSeq, c)
  const devMap = new Map()
  for (const d of devices.value) {
    if (d.agentId) devMap.set(d.agentId, d)
  }
  return stepAssignments.value.map(s => {
    const pStep = planSteps.find(ps => ps.stepSeq === s.stepSeq) || {}
    const cmd = cmdMap.get(s.stepSeq) || {}
    const dev = devMap.get(s.deviceAgentCode) || {}
    return {
      ...s,
      capabilityType: cmd.capabilityType || pStep.capabilityType || s.outputParams?.capabilityType,
      deviceName: dev.deviceName,
      deviceType: dev.simulatedDeviceType || dev.deviceTypeCode,
      inputParams: cmd.inputParams || pStep.inputParams || {}
    }
  })
})

const visibleSteps = computed(() => {
  if (mode.value === 'live') return mergedSteps.value
  if (playbackStep.value < 4) return []
  return mergedSteps.value
})

const activeDeviceStepMap = computed(() => {
  const map = {}
  for (const s of visibleSteps.value) {
    if (s.deviceAgentCode && (s.stepStatus === 'DISPATCHED' || s.stepStatus === 'EXECUTING')) {
      map[s.deviceAgentCode] = s.stepSeq
    }
  }
  return map
})

const collabEdges = computed(() => {
  const dest = effectiveDestPoint.value
  if (!dest) return []
  const edges = []
  for (const s of visibleSteps.value) {
    const dev = devices.value.find(d => d.agentId === s.deviceAgentCode)
    if (dev && dev.location && Number.isFinite(Number(dev.location.x))) {
      edges.push({ x1: Number(dev.location.x), y1: Number(dev.location.y), x2: dest.x, y2: dest.y })
    }
  }
  return edges
})

const deviceBubbles = computed(() => {
  const iconMap = {
    FLIGHT_DELAY_BOARD: '🛫',
    SMART_DISPLAY: '📺',
    BAGGAGE_SCANNER: '🧳',
    MOBILE_ROBOT: '🤖'
  }
  return visibleSteps.value.map(s => {
    const dtype = s.deviceType || inferTypeByCap(s.capabilityType)
    return {
      stepSeq: s.stepSeq,
      agentCode: s.deviceAgentCode || 'UNASSIGNED',
      icon: iconMap[dtype] || '📡',
      deviceLabel: s.deviceName || (dtype ? deviceTypeZh(dtype) : '待分派设备'),
      status: s.stepStatus,
      commandText: formatReadableCommand(s.capabilityType, s.inputParams) || capabilityLabel(s.capabilityType),
      feedbackText: formatReadableFeedback(s.outputParams, s.reasonCode)
    }
  })
})

function inferTypeByCap(cap) {
  if (cap === 'CAP_FLIGHT_UPDATE') return 'FLIGHT_DELAY_BOARD'
  if (cap === 'CAP_INFO_DISPLAY') return 'SMART_DISPLAY'
  if (cap === 'CAP_BAGGAGE_MEASURE' || cap === 'CAP_OVERSIZE_ALERT') return 'BAGGAGE_SCANNER'
  return 'MOBILE_ROBOT'
}

function deviceTypeZh(dtype) {
  const map = {
    FLIGHT_DELAY_BOARD: '航班信息屏仿真体',
    SMART_DISPLAY: '智慧显示终端仿真体',
    BAGGAGE_SCANNER: '行李测量仪仿真体',
    MOBILE_ROBOT: '移动服务机器人仿真体'
  }
  return map[dtype] || '智能设备'
}

function poiColor(cat) {
  return POI_CATEGORIES.find(c => c.key === cat)?.color || '#1677ff'
}

function poiBadge(cat) {
  return POI_CATEGORIES.find(c => c.key === cat)?.badge || '点'
}

function poiCategoryLabel(cat) {
  return POI_CATEGORIES.find(c => c.key === cat)?.label || cat
}

function capabilityLabel(cap) {
  const map = {
    CAP_FLIGHT_UPDATE: '航延屏信息发布',
    CAP_INFO_DISPLAY: '智慧航显引导展示',
    CAP_NOTIFICATION: '现场语音/人员通知',
    CAP_NAVIGATION: '机器人移动引导',
    CAP_ESCORT: '机器人陪同护送',
    CAP_BAGGAGE_MEASURE: '智能行李测量',
    CAP_OVERSIZE_ALERT: '超规行李告警上报'
  }
  return map[cap] || cap || '协同执行步骤'
}

function statusLabel(s) {
  const map = {
    SUBMITTED: '已提交', PLANNING: '待规划', VALIDATING: '校验中',
    EXECUTING: '执行中', COMPLETED: '已完成', FAILED: '已失败',
    PENDING_MANUAL: '待人工处理', MANUAL_TERMINATED: '已人工终止'
  }
  return map[s] || s || '—'
}

function statusColor(s) {
  if (s === 'COMPLETED') return 'green'
  if (s === 'FAILED' || s === 'PENDING_MANUAL') return 'red'
  if (s === 'EXECUTING' || s === 'PLANNING') return 'blue'
  return 'default'
}

function stepTagColor(s) {
  if (s === 'COMPLETED') return 'green'
  if (s === 'SKIPPED' || s === 'FAILED') return 'red'
  if (s === 'DISPATCHED' || s === 'EXECUTING') return 'blue'
  return 'default'
}

function isRunning(s) {
  return ['SUBMITTED', 'PLANNING', 'VALIDATING', 'EXECUTING', 'REPLANNING', 'PENDING_DISPATCH'].includes(s)
}

function stageStatus(idx) {
  if (visibleStageIndex.value > idx) return 'finish'
  if (visibleStageIndex.value === idx) return 'process'
  return 'wait'
}

function deviceMarkerClass(d) {
  if (d.onlineStatus !== 'ONLINE') return 'offline'
  if (d.workStatus === 'BUSY' || activeDeviceStepMap.value[d.agentId]) return 'busy'
  return 'online'
}

function filterTaskOption(input, option) {
  const text = String(option?.children?.[0]?.children || '')
  return text.toLowerCase().includes(input.toLowerCase())
}

function zoomBy(factor) {
  zoom.value = Math.min(2.0, Math.max(0.2, +(zoom.value * factor).toFixed(2)))
}

function fitAll() {
  zoom.value = 0.25
  pan.x = 180
  pan.y = 20
}

function focusActiveArea() {
  zoom.value = 0.65
  pan.x = 0
  pan.y = -1750
}

function handleWheel(e) {
  zoomBy(e.deltaY < 0 ? 1.12 : 0.88)
}

function startPan(e) {
  if (e.button !== 0) return
  dragging.value = true
  dragOrigin.x = e.clientX
  dragOrigin.y = e.clientY
  dragOrigin.panX = pan.x
  dragOrigin.panY = pan.y
}

function movePan(e) {
  if (viewportRef.value) {
    const rect = viewportRef.value.getBoundingClientRect()
    const mx = Math.round((e.clientX - rect.left - pan.x) / zoom.value)
    const my = Math.round((e.clientY - rect.top - pan.y) / zoom.value)
    if (mx >= 0 && mx <= MAP_WIDTH && my >= 0 && my <= MAP_HEIGHT) {
      cursorPos.value = { x: mx, y: my }
    }
  }
  if (!dragging.value) return
  pan.x = dragOrigin.panX + (e.clientX - dragOrigin.x)
  pan.y = dragOrigin.panY + (e.clientY - dragOrigin.y)
}

function endPan() {
  dragging.value = false
}

function togglePickPassenger() {
  drawMode.value = drawMode.value === 'PASSENGER' ? null : 'PASSENGER'
  drawPoints.value = []
}

function startDrawRegion(type) {
  drawMode.value = type
  drawPoints.value = []
}

function cancelDrawing() {
  drawMode.value = null
  drawPoints.value = []
}

function finishDrawing() {
  const minPts = (drawMode.value === 'ISOLATED_ZONE' || drawMode.value === 'CHECKIN_HALL') ? 3 : 2
  if (drawPoints.value.length < minPts) {
    message.warning(`至少需要点击 ${minPts} 个点`)
    return
  }
  regionNameInput.value = drawMode.value === 'ISOLATED_ZONE'
    ? '安检后候机隔离区'
    : drawMode.value === 'CHECKIN_HALL'
      ? '值机与行李托运办理区'
      : '候机厅通行走廊'
  regionNameModalOpen.value = true
}

async function handleSaveRegion() {
  const name = regionNameInput.value.trim()
  if (!name) {
    message.warning('请输入区域名称')
    return
  }
  const code = `${drawMode.value}_${Date.now()}`
  const res = await createMapRegion({
    regionCode: code,
    regionName: name,
    regionType: drawMode.value,
    geometryJson: JSON.stringify(drawPoints.value)
  })
  regions.value = res.data || []
  regionNameModalOpen.value = false
  drawMode.value = null
  drawPoints.value = []
  message.success('已保存空间区域配置')
}

async function handleDeleteRegion(id) {
  const res = await deleteMapRegion(id)
  regions.value = res.data || []
  message.success('已删除区域')
}

function handleMapClick(e) {
  if (!drawMode.value || !viewportRef.value) return
  const rect = viewportRef.value.getBoundingClientRect()
  const mx = Math.round((e.clientX - rect.left - pan.x) / zoom.value)
  const my = Math.round((e.clientY - rect.top - pan.y) / zoom.value)
  if (drawMode.value === 'PASSENGER') {
    const near = nearestPoi(mx, my, pois.value)
    manualPassengerPoint.value = { x: mx, y: my, label: near ? `${near.poiName}附近` : `(${mx}, ${my})` }
    if (near) quickForm.origin = near.poiCode
    drawMode.value = null
    message.success(`已设置旅客位置：${manualPassengerPoint.value.label}`)
  } else if (drawMode.value === 'POI_PICK') {
    poiForm.x = mx
    poiForm.y = my
    drawMode.value = null
    poiModalOpen.value = true
    message.success(`已拾取坐标 (${mx}, ${my})`)
  } else if (drawMode.value === 'ISOLATED_ZONE' || drawMode.value === 'CHECKIN_HALL' || drawMode.value === 'CORRIDOR') {
    drawPoints.value.push({ x: mx, y: my })
  }
}

function handlePoiClick(poi) {
  if (drawMode.value === 'PASSENGER') {
    manualPassengerPoint.value = { x: Number(poi.x), y: Number(poi.y), label: poi.poiName, code: poi.poiCode }
    quickForm.origin = poi.poiCode
    drawMode.value = null
    message.success(`已设置旅客起点：${poi.poiName}`)
  } else {
    message.info(`${poi.poiName}（${poiCategoryLabel(poi.category)}，坐标 ${Math.round(poi.x)}, ${Math.round(poi.y)}）`)
  }
}

function openPoiModal(record) {
  if (record) {
    Object.assign(poiForm, {
      id: record.id || null,
      poiCode: record.poiCode,
      poiName: record.poiName,
      category: record.category,
      x: Number(record.x),
      y: Number(record.y),
      zone: record.zone || '',
      linkedDeviceCode: record.linkedDeviceCode || null
    })
  } else {
    Object.assign(poiForm, {
      id: null,
      poiCode: '',
      poiName: '',
      category: 'GATE',
      x: 600,
      y: 4200,
      zone: '',
      linkedDeviceCode: null
    })
  }
  poiModalOpen.value = true
}

function startPickPoiCoord() {
  poiModalOpen.value = false
  spaceDrawerOpen.value = false
  drawMode.value = 'POI_PICK'
}

function handlePoiCategoryChange(val) {
  if (val === 'MEASURE' && scannerDevices.value.length && !poiForm.linkedDeviceCode) {
    const dev = scannerDevices.value[0]
    poiForm.linkedDeviceCode = dev.deviceCode
    handleScannerDeviceSelect(dev.deviceCode)
  }
}

function handleScannerDeviceSelect(code) {
  const dev = scannerDevices.value.find(d => d.deviceCode === code)
  if (dev && dev.location && Number.isFinite(Number(dev.location.x))) {
    poiForm.x = Number(dev.location.x)
    poiForm.y = Number(dev.location.y)
    if (!poiForm.poiName) poiForm.poiName = `${dev.deviceName}测量点`
    if (!poiForm.poiCode) poiForm.poiCode = `测量点_${dev.deviceCode}`
  }
}

async function handleSavePoi() {
  try {
    const res = poiForm.id
      ? await updatePoi(poiForm.id, { ...poiForm })
      : await createPoi({ ...poiForm })
    pois.value = res.data || []
    poiModalOpen.value = false
    message.success('POI 点位已保存')
  } catch (err) {
    message.error(err?.response?.data?.message || '保存 POI 失败')
  }
}

async function handleDeletePoi(id) {
  const res = await deletePoi(id)
  pois.value = res.data || []
  message.success('已删除 POI')
}

async function handleSyncScanners() {
  syncingScanners.value = true
  try {
    const res = await syncScannerPois()
    pois.value = res.data || []
    message.success('已自动同步智能行李测量仿真体实时坐标')
  } finally {
    syncingScanners.value = false
  }
}

async function loadMapLayoutData() {
  try {
    const res = await getMapLayout()
    if (res.data?.pois?.length) pois.value = res.data.pois
    regions.value = res.data?.regions || []
  } catch {
    // 回退默认内置 POI
  }
}

async function loadSnapshot() {
  const res = await request.get('/situation/snapshot')
  devices.value = res.data?.devices || []
}

async function loadTaskDetails(taskId) {
  if (!taskId) return
  const [tRes, pRes, cRes, sRes, eRes, cmdRes] = await Promise.all([
    getTask(taskId),
    getPlanVersions(taskId),
    getContextSnapshots(taskId),
    getStepAssignments(taskId),
    getTaskEvents(taskId),
    getTaskBoardCommands(taskId).catch(() => ({ data: [] }))
  ])
  currentTask.value = tRes.data
  planVersions.value = pRes.data || []
  contextSnapshots.value = cRes.data || []
  stepAssignments.value = sRes.data || []
  taskEvents.value = eRes.data || []
  taskCommands.value = cmdRes.data || []
}

async function refreshAll() {
  loading.value = true
  try {
    const [listRes] = await Promise.all([listTasks({ page: 1, size: 30 }), loadSnapshot(), loadMapLayoutData()])
    taskList.value = listRes.data?.content || []
    if (!selectedTaskId.value) {
      const qId = Number(route.query.taskId)
      selectedTaskId.value = qId || taskList.value[0]?.id || null
    }
    if (selectedTaskId.value) {
      await loadTaskDetails(selectedTaskId.value)
    }
  } finally {
    loading.value = false
  }
}

async function handleSelectTask(id) {
  manualPassengerPoint.value = null
  await loadTaskDetails(id)
  if (mode.value === 'playback') resetPlayback()
}

function resetPlayback() {
  playbackPlaying.value = false
  clearInterval(playbackTimer)
  playbackStep.value = 0
}

function togglePlayback() {
  if (mode.value !== 'playback') mode.value = 'playback'
  if (playbackPlaying.value) {
    playbackPlaying.value = false
    clearInterval(playbackTimer)
    return
  }
  if (playbackStep.value >= 4) playbackStep.value = 0
  playbackPlaying.value = true
  const intervalMs = Math.round(1500 / playbackSpeed.value)
  playbackTimer = setInterval(() => {
    if (playbackStep.value < 4) {
      playbackStep.value += 1
    } else {
      playbackPlaying.value = false
      clearInterval(playbackTimer)
    }
  }, intervalMs)
}

async function handleQuickSubmit() {
  quickSubmitting.value = true
  try {
    let payload
    if (quickForm.scenario === 'SPECIAL_PASSENGER_SERVICE') {
      const viaText = quickForm.viaSecurity ? `经${quickForm.viaSecurity}` : ''
      payload = {
        taskFamily: 'SPECIAL_PASSENGER_SERVICE',
        taskGoal: `请为虚构${quickForm.assistanceType}旅客在${quickForm.origin}通过智慧航显显示会合提示、通知现场人员，并安排服务机器人前往会合后${viaText}陪同旅客前往${quickForm.destination}。`,
        sceneParams: {
          assistanceType: quickForm.assistanceType,
          origin: quickForm.origin,
          viaSecurity: quickForm.viaSecurity || null,
          destination: quickForm.destination
        }
      }
    } else if (quickForm.scenario === 'FLIGHT_CHANGE_RESPONSE') {
      const today = new Date().toISOString().slice(0, 10)
      payload = {
        taskFamily: 'FLIGHT_CHANGE_RESPONSE',
        taskGoal: `虚构航班CA1234原计划22:30，延误30分钟至23:00，请通过航延屏发布变更、智慧航显发布提示，并由机器人引导旅客从${quickForm.origin}前往${quickForm.destination}。`,
        sceneParams: {
          eventSource: 'MANUAL_FORM',
          flightNumber: 'CA1234',
          changeType: 'DELAY',
          originalTime: `${today}T22:30:00`,
          newTime: `${today}T23:00:00`,
          origin: quickForm.origin,
          newGate: quickForm.destination,
          changeDescription: `虚构航班CA1234延误30分钟，登机口${quickForm.destination}`
        }
      }
    } else {
      payload = {
        taskFamily: 'OVERSIZE_BAGGAGE_HANDLING',
        taskGoal: `请测量${quickForm.origin}当前行李的长宽高和重量；超规时上报告警、由智慧航显发布${quickForm.destination}办理提示，并由移动机器人提供导航；正常行李留存测量结果后结束。`,
        sceneParams: {
          baggageLocation: quickForm.origin,
          targetCounter: quickForm.destination
        }
      }
    }
    const res = await submitTask(payload)
    quickModalOpen.value = false
    mode.value = 'live'
    manualPassengerPoint.value = null
    selectedTaskId.value = res.data.id
    await refreshAll()
    message.success(`已提交协同任务：${res.data.taskCode}`)
  } catch (err) {
    message.error(err?.response?.data?.message || '提交任务失败')
  } finally {
    quickSubmitting.value = false
  }
}

watch(mode, (val) => {
  if (val === 'live') {
    playbackPlaying.value = false
    clearInterval(playbackTimer)
    playbackStep.value = 5
  } else {
    resetPlayback()
  }
})

onMounted(async () => {
  await refreshAll()
  liveTimer = setInterval(async () => {
    if (mode.value === 'live' && selectedTaskId.value) {
      await Promise.all([loadSnapshot(), loadTaskDetails(selectedTaskId.value)]).catch(() => {})
    }
  }, 2000)
})

onBeforeUnmount(() => {
  clearInterval(liveTimer)
  clearInterval(playbackTimer)
})
</script>

<style scoped>
.board-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 12px;
  margin-bottom: 12px;
}
.board-header h2 { margin: 0; }
.board-header p { margin: 2px 0 0; color: #666; font-size: 13px; }
.map-toolbar { margin-bottom: 8px; }
.route-badge {
  background: #e6f4ff;
  color: #0958d9;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}
.map-viewport {
  position: relative;
  height: 620px;
  overflow: hidden;
  border: 1px solid #d9d9d9;
  border-radius: 6px;
  background: #f5f5f5;
  cursor: grab;
  user-select: none;
}
.map-viewport.picking { cursor: crosshair; }
.map-canvas { position: relative; }
.floorplan { width: 1260px; height: 6895px; display: block; pointer-events: none; }
.map-svg { position: absolute; left: 0; top: 0; width: 1260px; height: 6895px; pointer-events: none; }
.route-animated { animation: dashMove 1.2s linear infinite; }
@keyframes dashMove {
  to { stroke-dashoffset: -52; }
}
.poi-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 4px;
  cursor: pointer;
  z-index: 4;
}
.poi-dot {
  width: 22px;
  height: 22px;
  border-radius: 50%;
  background: var(--poi-color);
  color: #fff;
  font-size: 11px;
  font-weight: bold;
  display: flex;
  align-items: center;
  justify-content: center;
  border: 2px solid #fff;
  box-shadow: 0 2px 4px rgba(0,0,0,0.25);
}
.poi-label {
  background: rgba(255,255,255,0.92);
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  font-weight: 600;
  color: #262626;
  border: 1px solid #d9d9d9;
  white-space: nowrap;
}
.passenger-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  flex-direction: column;
  align-items: center;
  z-index: 12;
  pointer-events: none;
}
.passenger-pulse {
  position: absolute;
  width: 44px;
  height: 44px;
  border-radius: 50%;
  background: rgba(22, 119, 255, 0.25);
  animation: pulse 1.5s infinite;
}
.passenger-icon { font-size: 24px; position: relative; }
.passenger-label {
  background: #1677ff;
  color: #fff;
  padding: 1px 6px;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
}
.device-marker {
  position: absolute;
  transform: translate(-50%, -50%);
  display: flex;
  align-items: center;
  gap: 4px;
  z-index: 8;
}
.device-dot {
  width: 16px;
  height: 16px;
  border-radius: 50%;
  border: 2px solid #fff;
  box-shadow: 0 2px 6px rgba(0,0,0,0.35);
}
.device-marker.online .device-dot { background: #52c41a; }
.device-marker.busy .device-dot { background: #fa8c16; animation: pulse 1.2s infinite; }
.device-marker.offline .device-dot { background: #8c8c8c; }
.device-label {
  background: rgba(0,0,0,0.75);
  color: #fff;
  padding: 2px 6px;
  border-radius: 4px;
  font-size: 11px;
  white-space: nowrap;
}
@keyframes pulse {
  0% { transform: scale(1); opacity: 0.9; }
  70% { transform: scale(1.6); opacity: 0.2; }
  100% { transform: scale(1); opacity: 0.9; }
}
.map-footer {
  display: flex;
  justify-content: space-between;
  font-size: 12px;
  color: #888;
  margin-top: 6px;
}
.stage-desc { font-size: 12px; color: #444; }
.step-pill { display: flex; align-items: center; gap: 6px; margin-top: 4px; flex-wrap: wrap; }
.bubble-list { display: flex; flex-direction: column; gap: 10px; max-height: 260px; overflow-y: auto; }
.bubble-item {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  background: #fafafa;
  border: 1px solid #f0f0f0;
  border-radius: 8px;
  padding: 8px 10px;
}
.bubble-avatar {
  font-size: 24px;
  line-height: 1;
  background: #fff;
  border: 1px solid #e8e8e8;
  border-radius: 50%;
  width: 38px;
  height: 38px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
.bubble-content { flex: 1; font-size: 12px; }
.bubble-header { display: flex; justify-content: space-between; align-items: center; margin-bottom: 4px; }
.bubble-text { color: #333; word-break: break-word; }
</style>
