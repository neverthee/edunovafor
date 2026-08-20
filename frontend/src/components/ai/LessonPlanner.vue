<template>
  <div ref="plannerShellRef" class="lesson-planner-shell">
    <div
      class="planner-frame"
      :class="{
        'planner-frame--breakout': entryMode === 'create' || entryMode === 'result',
        'planner-frame--history-breakout': entryMode === 'history'
      }"
    >
      <Teleport v-if="showTeleportedCompactBar" :to="props.headerTarget">
        <div class="planner-compact-bar planner-compact-bar--teleported">
          <nav class="planner-steprail planner-steprail--inline planner-steprail--flow" aria-label="lesson-planner-steps">
            <template v-for="(item, idx) in compactFlowSteps" :key="item.index">
              <button
                type="button"
                class="flow-step"
                :class="{ active: currentStepIndex === item.index, complete: currentStepIndex > item.index }"
                @click="handleStepChipClick(item.index)"
              >
                <span class="flow-step-index">{{ item.index }}</span>
                <span class="flow-step-label">{{ item.label }}</span>
              </button>
              <span v-if="idx < compactFlowSteps.length - 1" class="flow-step-arrow" aria-hidden="true">
                <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
              </span>
            </template>
          </nav>

          <div class="planner-actions planner-actions--inline">
            <button type="button" class="compact-action-btn" @click="goToLauncher">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
              返回入口
            </button>
            <button v-if="entryMode !== 'history'" type="button" class="compact-action-btn history-btn" @click="openHistoryView">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
              备课历史
            </button>
          </div>
        </div>
      </Teleport>

      <header v-if="showLocalHeader" class="planner-header" :class="{ 'planner-header--compact': props.hideHeader, 'planner-header--with-steps': entryMode !== 'launcher' }">
        <template v-if="showInlineCompactBar">
          <div class="planner-compact-bar">
            <nav class="planner-steprail planner-steprail--inline planner-steprail--flow" aria-label="lesson-planner-steps">
              <template v-for="(item, idx) in compactFlowSteps" :key="item.index">
                <button
                  type="button"
                  class="flow-step"
                  :class="{ active: currentStepIndex === item.index, complete: currentStepIndex > item.index }"
                  @click="handleStepChipClick(item.index)"
                >
                  <span class="flow-step-index">{{ item.index }}</span>
                  <span class="flow-step-label">{{ item.label }}</span>
                </button>
                <span v-if="idx < compactFlowSteps.length - 1" class="flow-step-arrow" aria-hidden="true">
                  <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
                </span>
              </template>
            </nav>

            <div class="planner-actions planner-actions--inline">
              <button type="button" class="compact-action-btn" @click="goToLauncher">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
                返回入口
              </button>
              <button v-if="entryMode !== 'history'" type="button" class="compact-action-btn history-btn" @click="openHistoryView">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
                备课历史
              </button>
            </div>
          </div>
        </template>

        <template v-else>
        <div class="planner-header-main" :class="{ 'planner-header-main--compact': props.hideHeader }">
          <div v-if="!props.hideHeader">
            <div class="planner-kicker">Lesson Planning Studio</div>
            <h2 class="planner-title">智能备课</h2>
            <p class="planner-subtitle">从教学思路到备课产出，按步骤整理课程、资源与核心需求。</p>
          </div>
          <div v-if="entryMode !== 'launcher'" class="planner-actions" :class="{ 'planner-actions--full': props.hideHeader }">
            <button type="button" class="compact-action-btn" @click="goToLauncher">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m12 19-7-7 7-7"/><path d="M19 12H5"/></svg>
              返回入口
            </button>
            <button v-if="entryMode !== 'history'" type="button" class="compact-action-btn history-btn" @click="openHistoryView">
              <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
              备课历史
            </button>
          </div>
        </div>

        <nav v-if="entryMode !== 'launcher'" class="planner-steprail" aria-label="lesson-planner-steps">
          <button
            v-for="item in stepItems"
            :key="item.index"
            type="button"
            class="step-chip"
            :class="{ active: currentStepIndex === item.index, complete: currentStepIndex > item.index }"
            @click="handleStepChipClick(item.index)"
          >
            <span class="step-chip-index">{{ item.index }}</span>
            <span class="step-chip-copy">
              <span class="step-chip-kicker">{{ item.index === 0 ? '入口' : `步骤 ${item.index}` }}</span>
              <span class="step-chip-label">{{ item.label }}</span>
            </span>
          </button>
        </nav>
        </template>
      </header>

      <section v-if="entryMode === 'launcher'" class="launcher-stage">
        <div class="launcher-welcome">
          <div class="welcome-badge">AI Powered</div>
          <h2 class="welcome-title">智能备课中心</h2>
          <p class="welcome-desc">利用大模型能力，高效生成专业教案、课件与互动教学方案</p>
        </div>
        
        <div class="launcher-grid">
          <button type="button" class="launcher-card create-card" @click="startCreateFlow">
            <div class="launcher-card-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
            </div>
            <div class="launcher-card-content">
              <span class="launcher-card-kicker">Step 0</span>
              <span class="launcher-card-title">新建备课</span>
              <span class="launcher-card-body">按课程、资源、需求三步整理，最后生成 Word、PPT 与互动小游戏方案。</span>
            </div>
            <div class="launcher-card-arrow">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
            </div>
          </button>
          
          <button type="button" class="launcher-card launcher-card--history" @click="openHistoryView">
            <div class="launcher-card-icon">
              <svg xmlns="http://www.w3.org/2000/svg" width="32" height="32" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M3 12a9 9 0 1 0 9-9 9.75 9.75 0 0 0-6.74 2.74L3 8"/><path d="M3 3v5h5"/><path d="M12 7v5l4 2"/></svg>
            </div>
            <div class="launcher-card-content">
              <span class="launcher-card-kicker">Archive</span>
              <span class="launcher-card-title">备课历史</span>
              <span class="launcher-card-body">查看已生成的结构化版本，继续导出、回退旧版或增量修订。</span>
            </div>
            <div class="launcher-card-arrow">
              <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m9 18 6-6-6-6"/></svg>
            </div>
          </button>
        </div>
      </section>

      <section
        v-else-if="entryMode === 'create'"
        class="workspace-grid"
        :class="{ 'workspace-grid--breakout': true }"
      >
        <div class="stage-panel">
          <div v-if="wizardStep === 1" class="stage-card step-one-card step-form-card">
            <div class="stage-header">
              <div class="stage-header-content">
                <h3>选择课程与章节</h3>
                <p>请指定本次备课的基础课程信息及适用的学段学科</p>
              </div>
            </div>

            <div class="stage-form-grid">
              <label class="field-group">
                <span class="field-label">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="field-icon"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M8 7h6"/><path d="M8 11h8"/></svg>
                  选择课程 <em>*</em>
                </span>
                <select v-model="formData.courseId" class="planner-select" :class="{ 'is-placeholder': !formData.courseId }">
                  <option value="">请选择课程</option>
                  <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
                </select>
              </label>

              <label class="field-group">
                <span class="field-label">
                  <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="field-icon"><path d="M11 3H4v18h16V7l-4-4z"/><path d="m14 10-4 4"/><path d="m10 10 4 4"/></svg>
                  选择章节 <em>*</em>
                </span>
                <select v-model="formData.chapterId" class="planner-select" :class="{ 'is-placeholder': !formData.chapterId }" :disabled="!formData.courseId">
                  <option value="">请选择章节</option>
                  <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">{{ chapter.title }}</option>
                </select>
              </label>
            </div>

            <div class="field-block">
              <div class="field-label">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="field-icon"><path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10Z"/></svg>
                学段 / 年级 / 学科 <em>*</em>
              </div>
              <div class="grade-grid">
                <div class="input-with-label">
                  <input v-model="gradeDraft.stage" type="text" class="planner-input" placeholder="学段 (如：高中)" />
                </div>
                <div class="input-with-label">
                  <input v-model="gradeDraft.grade" type="text" class="planner-input" placeholder="年级 (如：高一)" />
                </div>
                <div class="input-with-label">
                  <input v-model="gradeDraft.subject" type="text" class="planner-input" placeholder="学科 (如：数学)" />
                </div>
              </div>
            </div>

            <div class="field-block">
              <div class="field-label">
                <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="field-icon"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="7 10 12 15 17 10"/><line x1="12" y1="15" x2="12" y2="3"/></svg>
                所需课件 <em>*</em>
              </div>
              <div class="deliverable-grid">
                <button
                  v-for="option in deliveryOptions"
                  :key="option.value"
                  type="button"
                  class="deliverable-card"
                  :class="{ active: deliverables.includes(option.value), locked: isDeliverableLocked(option.value) }"
                  @click="toggleDeliverable(option.value)"
                >
                  <div class="deliverable-card-icon">
                    <svg v-if="option.value === 'word'" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/></svg>
                    <svg v-if="option.value === 'ppt'" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="2" y="3" width="20" height="14" rx="2" ry="2"/><line x1="8" y1="21" x2="16" y2="21"/><line x1="12" y1="17" x2="12" y2="21"/></svg>
                    <svg v-if="option.value === 'game'" xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M14.5 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V7.5L14.5 2z"/><polyline points="14 2 14 8 20 8"/><path d="M9 13v4"/><path d="M12 13v4"/><path d="M15 13v4"/></svg>
                  </div>
                  <div class="deliverable-card-content">
                    <span class="deliverable-card-title">{{ option.label }}</span>
                    <span class="deliverable-card-body">{{ option.description }}</span>
                  </div>
                  <div class="deliverable-check">
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                  </div>
                </button>
              </div>
              <p class="field-hint">注：选择互动小游戏时会自动包含 PPT 课件。</p>
            </div>

            <div class="stage-footer">
              <button type="button" class="planner-ghost-button" @click="goToLauncher">返回入口</button>
              <button type="button" class="planner-primary-button" :disabled="!canMoveFromStepOne" @click="wizardStep = 2">
                下一步：选择资源
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" style="margin-left: 4px;"><path d="m9 18 6-6-6-6"/></svg>
              </button>
            </div>
          </div>

          <div v-else-if="wizardStep === 2" class="stage-card step-form-card step-resource-card">
            <div class="stage-header">
              <div class="stage-header-content">
                <h3>选择备课资源</h3>
                <p>上传本地文件或从知识库中引入参考资料，支持多格式解析</p>
              </div>
            </div>

            <div class="resource-columns-modern">
              <section class="resource-card-modern">
                <div class="resource-card-head">
                  <div class="head-info">
                    <h4>
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="head-icon"><path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4"/><polyline points="17 8 12 3 7 8"/><line x1="12" y1="3" x2="12" y2="15"/></svg>
                      上传本地文件
                    </h4>
                    <p>支持文档、图片和视频。单文件上限 200MB，视频上传可能需要更久。</p>
                  </div>
                  <label class="upload-trigger-modern" :class="{ disabled: pendingUploadedFiles.length > 0 }">
                    <input type="file" class="sr-only" accept=".pdf,.docx,.doc,.txt,.md,.ppt,.pptx,.jpg,.jpeg,.png,.webp,.mp4,.mov,.avi,.mkv,.webm" :disabled="pendingUploadedFiles.length > 0" @change="handleFileUpload" />
                    <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 6px;"><path d="M5 12h14"/><path d="M12 5v14"/></svg>
                    {{ pendingUploadedFiles.length > 0 ? '上传中...' : '上传文件' }}
                  </label>
                </div>

                <div v-if="uploadedFiles.length === 0" class="empty-resource-placeholder">
                  <p>暂未上传任何本地文件</p>
                </div>
                <div v-else class="resource-list-modern">
                  <article v-for="file in uploadedFiles" :key="file.clientId" class="resource-item-modern" :class="{ 'is-uploading': file.status === 'uploading', 'is-failed': file.status === 'failed' }">
                    <div class="item-header">
                      <div class="file-info">
                        <span class="file-type-icon">{{ getFileTypeBadge(file.name) }}</span>
                        <div class="file-meta">
                          <div class="file-name">{{ file.name }}</div>
                          <div class="file-submeta">
                            <span v-if="file.size">{{ formatFileSize(file.size) }}</span>
                            <span class="status-chip" :class="file.status">{{ getUploadStatusLabel(file) }}</span>
                          </div>
                        </div>
                      </div>
                      <button type="button" class="remove-btn-icon" @click="removeFile(file)">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                      </button>
                    </div>
                    <div v-if="file.status !== 'ready'" class="upload-status-panel" :class="file.status">
                      <div v-if="file.status === 'uploading'" class="upload-progress-shell">
                        <div class="upload-progress-bar" :style="{ width: `${Math.max(file.progress, 4)}%` }"></div>
                      </div>
                      <p class="upload-status-copy">
                        {{ file.status === 'uploading'
                          ? (file.progress > 0 ? `正在上传，请保持页面开启。当前进度 ${file.progress}%` : '正在准备上传，请稍候...')
                          : (file.errorMessage || '上传失败，请删除后重新选择文件。') }}
                      </p>
                    </div>
                    <div class="item-form-grid">
                      <div class="field-group-modern">
                        <label class="field-label">用途</label>
                        <select v-model="file.usage" class="planner-select-modern" :class="{ 'is-invalid': shouldHighlightSourceField(file, 'usage') }" :disabled="file.status !== 'ready'">
                          <option value="">选择用途</option>
                          <option v-for="option in sourceUsageOptions" :key="option.value" :value="option.label">{{ option.label }}</option>
                        </select>
                      </div>
                      <div class="field-group-modern">
                        <label class="field-label">知识点</label>
                        <input v-model="file.knowledgePoint" type="text" class="planner-input-modern" :class="{ 'is-invalid': shouldHighlightSourceField(file, 'knowledgePoint') }" :disabled="file.status !== 'ready'" placeholder="关联知识点" />
                      </div>
                      <div class="field-group-modern">
                        <label class="field-label">必选</label>
                        <select v-model="file.isRequired" class="planner-select-modern" :class="{ 'is-invalid': shouldHighlightSourceField(file, 'isRequired') }" :disabled="file.status !== 'ready'">
                          <option :value="null">请选择</option>
                          <option :value="true">是</option>
                          <option :value="false">否</option>
                        </select>
                      </div>
                    </div>
                  </article>
                  <div class="resource-actions-modern">
                    <button type="button" class="process-btn" :disabled="!canProcessSources" @click="processUploadedSources">
                      {{ isProcessingSources ? '解析中...' : '解析上传资料' }}
                    </button>
                    <span v-if="processedSourcesDirty" class="status-badge warn">建议重新解析</span>
                    <span v-else-if="processedSources.length > 0" class="status-badge success">解析已完成</span>
                  </div>
                </div>
              </section>

              <section class="resource-card-modern">
                <div class="resource-card-head">
                  <div class="head-info">
                    <h4>
                      <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" class="head-icon"><path d="M4 19.5v-15A2.5 2.5 0 0 1 6.5 2H20v20H6.5a2.5 2.5 0 0 1-2.5-2.5Z"/><path d="M8 7h6"/><path d="M8 11h8"/></svg>
                      从知识库引用
                    </h4>
                  </div>
                </div>

                <div class="knowledge-picker-modern">
                  <button type="button" class="picker-trigger" :class="{ active: knowledgePickerOpen }" :disabled="selectableKnowledgeItems.length === 0" @click="toggleKnowledgePicker">
                    <span>{{ knowledgePickerTriggerLabel }}</span>
                    <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" :style="{ transform: knowledgePickerOpen ? 'rotate(180deg)' : 'none', transition: 'transform 0.3s' }"><path d="m6 9 6 6 6-6"/></svg>
                  </button>

                  <div v-if="knowledgePickerOpen" class="picker-dropdown">
                    <div class="picker-search">
                      <input v-model.trim="knowledgeSearchQuery" type="text" class="picker-search-input" placeholder="搜索知识库..." />
                    </div>
                    <div class="picker-options">
                      <button v-for="item in filteredKnowledgeOptions" :key="item.id" type="button" class="picker-option" :class="{ active: isKnowledgeItemSelected(item) }" @click="toggleKnowledgeItem(item)">
                        <div class="option-info">
                          <div class="option-title">{{ getFileName(item.file_path) }}</div>
                          <div class="option-meta">{{ getKnowledgePurposeLabel(item.purpose) }}</div>
                        </div>
                        <div class="option-check" v-if="isKnowledgeItemSelected(item)">
                          <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                        </div>
                      </button>
                    </div>
                  </div>
                </div>

                <div v-if="selectedKnowledgeItems.length > 0" class="resource-list-modern">
                  <article v-for="item in selectedKnowledgeItems" :key="item.id" class="resource-item-modern kb-item">
                    <div class="item-header">
                      <div class="file-info">
                        <span class="file-type-icon kb">KB</span>
                        <div class="file-meta">
                          <div class="file-name">{{ getFileName(item.file_path) }}</div>
                        </div>
                      </div>
                      <button type="button" class="remove-btn-icon" @click="removeKnowledgeItem(item.id)">
                        <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><path d="M18 6 6 18"/><path d="m6 6 12 12"/></svg>
                      </button>
                    </div>
                    <div class="item-form-grid">
                      <div class="field-group-modern">
                        <label class="field-label">用途</label>
                        <select v-model="item.usage" class="planner-select-modern" :class="{ 'is-invalid': shouldHighlightKnowledgeField(item, 'usage') }">
                          <option value="">选择用途</option>
                          <option v-for="option in sourceUsageOptions" :key="option.value" :value="option.label">{{ option.label }}</option>
                        </select>
                      </div>
                      <div class="field-group-modern">
                        <label class="field-label">知识点</label>
                        <input v-model="item.knowledgePoint" type="text" class="planner-input-modern" :class="{ 'is-invalid': shouldHighlightKnowledgeField(item, 'knowledgePoint') }" placeholder="关联知识点" />
                      </div>
                      <div class="field-group-modern">
                        <label class="field-label">必选</label>
                        <select v-model="item.isRequired" class="planner-select-modern" :class="{ 'is-invalid': shouldHighlightKnowledgeField(item, 'isRequired') }">
                          <option :value="null">请选择</option>
                          <option :value="true">是</option>
                          <option :value="false">否</option>
                        </select>
                      </div>
                    </div>
                  </article>
                </div>
              </section>
            </div>

            <div v-if="resourceStepGuideMessage" class="stage-guide-modern" :class="{ warn: !canMoveFromResourceStep }">
              <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 8px;"><circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/><line x1="12" y1="16" x2="12.01" y2="16"/></svg>
              <span>{{ resourceStepGuideMessage }}</span>
            </div>

            <div class="stage-footer">
              <button type="button" class="planner-ghost-button" @click="wizardStep = 1">
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><path d="m15 18-6-6 6-6"/></svg>
                上一步
              </button>
              <button type="button" class="planner-primary-button" :disabled="!canMoveFromResourceStep" @click="goToRequirementStep">
                {{ canMoveFromResourceStep ? '下一步：确认需求' : '请补全资料标注' }}
                <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-left: 4px;"><path d="m9 18 6-6-6-6"/></svg>
              </button>
            </div>
          </div>

          <div v-else class="stage-card step-form-card step-requirement-card">
            <div class="stage-header">
              <div class="stage-header-content">
                <h3>确认备课需求</h3>
                <p>与智能助手交流您的教学构想，系统将自动为您梳理核心配置</p>
              </div>
              <div class="stage-header-actions">
                <button type="button" class="planner-primary-button" :disabled="!canGenerate" @click="generateLessonPlan">
                  {{ isGenerating ? '正在生成课件...' : '立即生成备课内容' }}
                  <svg v-if="!isGenerating" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-left: 6px;"><path d="M21 12a9 9 0 1 1-9-9c2.52 0 4.93 1 6.74 2.74L21 8"/><path d="M21 3v5h-5"/></svg>
                </button>
              </div>
            </div>

            <div class="assistant-stage-modern">
              <div class="chat-thread-container" ref="chatThreadContainer">
                <div class="assistant-thread-modern">
                  <article v-for="turn in chatTranscript" :key="turn.timestamp" class="chat-row-modern" :class="turn.role">
                    <div v-if="turn.role === 'assistant'" class="ai-avatar-modern">
                      <div class="ai-icon-glow">
                        <img src="@/assets/images/atom.png" alt="AI" />
                      </div>
                    </div>
                    <div v-else class="user-avatar-modern" aria-hidden="true">
                      <img
                        v-if="currentUserAvatarUrl"
                        :src="formatUserAvatarUrl(currentUserAvatarUrl)"
                        alt="用户头像"
                        class="user-avatar-image-modern"
                      />
                      <span v-else>{{ currentUserAvatarInitial }}</span>
                    </div>
                    
                    <div class="bubble-wrapper">
                      <div class="bubble-modern" :class="turn.role">
                        <div class="chat-paragraphs">
                          <p v-for="(paragraph, index) in getChatParagraphs(turn.content)" :key="index">{{ paragraph }}</p>
                        </div>

                        <!-- 需求清单现代版 -->
                        <div v-if="turn.role === 'assistant' && turn.requirementChecklist?.length" class="requirement-checklist-modern">
                          <div
                            v-for="item in turn.requirementChecklist"
                            :key="item.key"
                            class="check-item-modern"
                            :class="item.status"
                          >
                            <div class="check-icon-modern">
                              <svg v-if="item.status === 'done'" xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><polyline points="20 6 9 17 4 12"/></svg>
                              <svg v-else xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="3" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><line x1="12" y1="16" x2="12" y2="12"/><line x1="12" y1="8" x2="12.01" y2="8"/></svg>
                            </div>
                            <div class="check-content-modern">
                              <div class="check-label">{{ item.label }}</div>
                              <div class="check-detail">{{ item.detail }}</div>
                            </div>
                          </div>
                        </div>

                        <!-- 追问引导 -->
                        <div v-if="turn.role === 'assistant' && turn.followupQuestion" class="followup-box-modern">
                          <div class="followup-label">
                            <svg xmlns="http://www.w3.org/2000/svg" width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M21 11.5a8.38 8.38 0 0 1-.9 3.8 8.5 8.5 0 0 1-7.6 4.7 8.38 8.38 0 0 1-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 0 1-.9-3.8 8.5 8.5 0 0 1 4.7-7.6 8.38 8.38 0 0 1 3.8-.9h.5a8.48 8.48 0 0 1 8 8v.5z"/></svg>
                            建议下一步
                          </div>
                          <p>{{ turn.followupQuestion }}</p>
                        </div>

                        <!-- 快捷选项 -->
                        <div v-if="turn.role === 'assistant' && turn.quickPrompts?.length" class="quick-prompts-modern">
                          <button
                            v-for="prompt in turn.quickPrompts"
                            :key="prompt"
                            type="button"
                            class="prompt-pill-modern"
                            @click="appendFollowupPrompt(prompt)"
                          >
                            {{ prompt }}
                          </button>
                        </div>
                      </div>
                    </div>
                  </article>
                </div>
              </div>

              <!-- 输入区域 -->
              <div class="input-section-modern">
                <form class="compose-box-modern" @submit.prevent="submitTeachingIdea">
                  <div class="textarea-wrapper-modern">
                    <textarea
                      v-model="chatDraft"
                      class="chat-textarea-modern"
                      placeholder="在这里输入您的备课想法..."
                      rows="1"
                      @keydown.enter.exact.prevent="submitTeachingIdea"
                    />
                    <div class="compose-actions-modern">
                      <div class="status-indicators">
                        <div v-if="isRecording" class="recording-pulse">
                          <span class="pulse-dot"></span>
                          录音中
                        </div>
                        <div v-if="isTranscribing" class="transcribing-spin">
                          <div class="mini-spinner-dark"></div>
                          转写中
                        </div>
                      </div>
                      
                      <div class="button-group-modern">
                        <button
                          v-if="!isRecording"
                          type="button"
                          class="circle-btn-modern voice-btn"
                          :disabled="isTranscribing"
                          title="语音输入"
                          aria-label="语音输入"
                          @click="startRecording"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M12 2a3 3 0 0 0-3 3v7a3 3 0 0 0 6 0V5a3 3 0 0 0-3-3Z"/><path d="M19 10v2a7 7 0 0 1-14 0v-2"/><line x1="12" y1="19" x2="12" y2="22"/></svg>
                        </button>
                        <button
                          v-else
                          type="button"
                          class="circle-btn-modern stop-btn pulse-red"
                          @click="stopRecording"
                          title="停止录音"
                          aria-label="停止录音"
                        >
                          <svg xmlns="http://www.w3.org/2000/svg" width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect width="10" height="10" x="7" y="7" rx="2"/></svg>
                        </button>
                        
                        <button
                          type="submit"
                          class="send-btn-modern"
                          :disabled="!chatDraft.trim() || isSummarizingRequirement || isStructuringRequirement"
                          title="发送构思"
                          aria-label="发送构思"
                        >
                          <span>发送构思</span>
                          <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m22 2-7 20-4-9-9-4Z"/><path d="M22 2 11 13"/></svg>
                        </button>
                      </div>
                    </div>
                  </div>
                </form>

                <div v-if="showLessonGenerationProgress" class="progress-card-modern">
                  <div class="progress-info-modern">
                    <div class="task-label">{{ activeProgressTask?.label }}</div>
                    <div class="task-percent">{{ displayProgressPercent }}%</div>
                  </div>
                  <div class="progress-bar-track-modern">
                    <div class="progress-bar-fill-modern" :style="{ width: `${displayProgressPercent}%` }"></div>
                  </div>
                  <div class="task-detail-modern">{{ activeProgressTask?.detail }}</div>
                </div>
              </div>

              <div class="stage-footer">
                <button type="button" class="planner-ghost-button" @click="wizardStep = 2">
                  <svg xmlns="http://www.w3.org/2000/svg" width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round" style="margin-right: 4px;"><path d="m15 18-6-6 6-6"/></svg>
                  上一步
                </button>
              </div>
            </div>
          </div>
        </div>

        <aside class="summary-panel" :class="{ open: showSummaryPanel, collapsed: !showSummaryPanel }">
          <div class="summary-panel-head">
            <div class="summary-header-main">
              <div class="summary-badge">Summary</div>
              <h3>{{ currentStepSummaryTitle }}</h3>
              <p v-if="showSummaryPanel" class="summary-hint">实时预览您的备课配置</p>
            </div>
            <button type="button" class="summary-toggle-btn" :class="{ active: showSummaryPanel }" @click="showSummaryPanel = !showSummaryPanel">
              <svg xmlns="http://www.w3.org/2000/svg" width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="m15 18-6-6 6-6"/></svg>
            </button>
          </div>

          <div class="summary-panel-body" :class="{ collapsed: !showSummaryPanel }">
            <div class="summary-panel-body-inner">
              <section class="summary-card summary-readonly-card">
                <h4>{{ wizardStep === 1 ? '课程选择' : '课程与产出' }}</h4>
                <dl class="summary-grid course-summary-grid" :class="{ compact: wizardStep === 1 }">
                  <div>
                    <dt>课程</dt>
                    <dd :class="{ empty: !getCourseNameById(formData.courseId) }">{{ getCourseNameById(formData.courseId) || '未选择' }}</dd>
                  </div>
                  <div>
                    <dt>章节</dt>
                    <dd :class="{ empty: !getChapterTitleById(formData.chapterId) }">{{ getChapterTitleById(formData.chapterId) || '未选择' }}</dd>
                  </div>
                  <div v-if="wizardStep >= 2">
                    <dt>学段 / 年级 / 学科</dt>
                    <dd :class="{ empty: !gradeSubjectText }">{{ gradeSubjectText || '未填写' }}</dd>
                  </div>
                  <div v-if="wizardStep >= 2">
                    <dt>所需课件</dt>
                    <dd :class="{ empty: !deliverables.length }">{{ deliverableSummaryText }}</dd>
                  </div>
                </dl>
              </section>

              <section v-if="wizardStep >= 2" class="summary-card summary-readonly-card">
                <h4>资源选择</h4>
                <div class="summary-list">
                  <div class="summary-stat">上传文件：{{ uploadedFiles.length }}</div>
                  <div class="summary-stat">知识库文件：{{ selectedKnowledgeItems.length }}</div>
                </div>
                <div v-if="uploadedFiles.length > 0" class="summary-tags">
                  <button v-for="file in uploadedFiles" :key="file.path" type="button" class="tag removable" @click="removeFile(file)">
                    {{ file.name }}
                  </button>
                </div>
                <div v-if="selectedKnowledgeItems.length > 0" class="summary-tags">
                  <button v-for="item in selectedKnowledgeItems" :key="item.id" type="button" class="tag removable muted" @click="removeKnowledgeItem(item.id)">
                    {{ getFileName(item.file_path) }}
                  </button>
                </div>
                <p v-if="uploadedFiles.length === 0 && selectedKnowledgeItems.length === 0" class="summary-empty">暂无额外资源。</p>
              </section>

              <section v-if="wizardStep >= 3" class="summary-card editable-card-modern">
                <div class="summary-card-header">
                  <h4>核心教学需求</h4>
                </div>
                
                <div class="editable-grid-modern">
                  <div class="field-group-modern">
                    <label class="field-label-modern">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><circle cx="12" cy="12" r="10"/><polyline points="12 6 12 12 16 14"/></svg>
                      课时长度 <em>*</em>
                    </label>
                    <input v-model="requirementDraft.duration" type="text" class="planner-input-modern compact" placeholder="如：45分钟" />
                  </div>

                  <div class="field-group-modern full-span">
                    <label class="field-label-modern">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M22 11.08V12a10 10 0 1 1-5.93-9.14"/><polyline points="22 4 12 14.01 9 11.01"/></svg>
                      核心教学目标 <em>*</em>
                    </label>
                    <textarea v-model="requirementDraft.objectives" rows="2" class="planner-textarea-modern compact" placeholder="描述学生应掌握的核心目标" />
                  </div>

                  <div class="field-group-modern full-span">
                    <label class="field-label-modern">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="m12 14 4-4"/><path d="M3.34 19a10 10 0 1 1 17.32 0"/><path d="m9.07 14.93 4.24-4.24"/><path d="m14.93 9.07 4.24-4.24"/></svg>
                      教学重点与难点
                    </label>
                    <div class="dual-input-modern">
                      <input v-model="requirementDraft.keyPoints" type="text" class="planner-input-modern compact" placeholder="重点" />
                      <input v-model="requirementDraft.difficultPoints" type="text" class="planner-input-modern compact" placeholder="难点" />
                    </div>
                  </div>

                  <div class="field-group-modern">
                    <label class="field-label-modern">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 19l7-7 3 3-7 7-3-3z"/><path d="M18 13l-1.5-7.5L2 2l3.5 14.5L13 18l5-5z"/><path d="M2 2l7.586 7.586"/><circle cx="11" cy="11" r="2"/></svg>
                      教学风格
                    </label>
                    <input v-model="requirementDraft.teachingStyle" list="teaching-style-options" type="text" class="planner-input-modern compact" placeholder="如：探究式" />
                  </div>

                  <div class="field-group-modern">
                    <label class="field-label-modern">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M16 21v-2a4 4 0 0 0-4-4H6a4 4 0 0 0-4 4v2"/><circle cx="9" cy="7" r="4"/><path d="M22 21v-2a4 4 0 0 0-3-3.87"/><path d="M16 3.13a4 4 0 0 1 0 7.75"/></svg>
                      学情预设
                    </label>
                    <select v-model="requirementDraft.studentPreset" class="planner-select-modern compact">
                      <option v-for="option in studentPresetOptions" :key="option" :value="option">{{ option }}</option>
                    </select>
                  </div>

                  <div class="field-group-modern full-span">
                    <label class="field-label-modern">
                      <svg xmlns="http://www.w3.org/2000/svg" width="12" height="12" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5" stroke-linecap="round" stroke-linejoin="round"><path d="M12 20h9"/><path d="M16.5 3.5a2.121 2.121 0 0 1 3 3L7 19l-4 1 1-4L16.5 3.5z"/></svg>
                      课堂类型
                    </label>
                    <div class="choice-grid-modern">
                      <button
                        v-for="activity in activityOptions"
                        :key="activity"
                        type="button"
                        class="choice-chip-modern"
                        :class="{ active: requirementDraft.activities.includes(activity) }"
                        @click="toggleActivity(activity)"
                      >
                        {{ activity }}
                      </button>
                    </div>
                  </div>
                </div>
              </section>
            </div>
          </div>
        </aside>
      </section>

      <section v-else-if="entryMode === 'history'">
        <div v-if="!selectedHistoryId" class="mx-auto max-w-4xl py-10 px-4 sm:px-6 lg:px-8 w-full">
          <div class="bg-white rounded-2xl shadow-sm border border-gray-100 overflow-hidden">
            <div class="px-8 py-6 border-b border-gray-50 flex items-center justify-between bg-gray-50/30">
              <div>
                <span class="inline-flex items-center rounded-md bg-purple-50 px-2 py-1 text-xs font-medium text-purple-700 ring-1 ring-inset ring-purple-700/10 mb-3">
                  History
                </span>
                <h3 class="text-xl font-semibold text-gray-900 tracking-tight">备课历史</h3>
                <p class="mt-1 text-sm text-gray-500">先选择一条历史记录，随后再进入与生成结果页相同的预览结构。</p>
              </div>
              <button 
                type="button" 
                class="inline-flex items-center justify-center rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm font-medium text-gray-600 shadow-sm hover:bg-gray-50 hover:text-gray-900 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-all"
                @click="fetchHistoryRecords"
              >
                <svg class="mr-2 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
                刷新
              </button>
            </div>

            <div v-if="isLoadingHistory" class="flex flex-col items-center justify-center py-24 px-4">
              <div class="relative h-10 w-10">
                <div class="absolute inset-0 rounded-full border-2 border-purple-100"></div>
                <div class="absolute inset-0 animate-spin rounded-full border-2 border-purple-600 border-t-transparent"></div>
              </div>
              <p class="mt-4 text-sm font-medium text-gray-500">正在加载历史记录...</p>
            </div>
            
            <div v-else-if="historyRecords.length === 0" class="flex flex-col items-center justify-center py-24 px-4">
              <div class="flex h-12 w-12 items-center justify-center rounded-full bg-gray-50 mb-4">
                <svg class="h-6 w-6 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
              </div>
              <p class="text-sm font-medium text-gray-500">暂无备课历史</p>
            </div>
            
            <div v-else class="divide-y divide-gray-50">
              <div
                v-for="record in historyRecords"
                :key="record.conversation_id"
                class="group relative flex items-center justify-between px-8 py-5 transition-colors hover:bg-gray-50/80 cursor-pointer"
                @click="loadHistoryRecord(record.conversation_id)"
              >
                <div class="min-w-0 flex-1 flex items-center">
                  <div class="mr-4 flex h-10 w-10 flex-shrink-0 items-center justify-center rounded-lg bg-purple-50 text-purple-600 group-hover:bg-purple-100 transition-colors">
                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" /></svg>
                  </div>
                  <div class="min-w-0 flex-1">
                    <h4 class="truncate text-base font-medium text-gray-900 transition-colors group-hover:text-purple-600">
                      {{ getHistoryRecordTitle(record) }}
                    </h4>
                    <p class="mt-1 truncate text-xs text-gray-400 font-mono flex items-center gap-2">
                      <span>ID: {{ record.conversation_id.substring(0, 8) }}</span>
                      <span v-if="record.created_at">•</span>
                      <span v-if="record.created_at">{{ new Date(record.created_at).toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' }) }}</span>
                    </p>
                  </div>
                </div>
                
                <div class="ml-4 flex flex-shrink-0 items-center opacity-0 group-hover:opacity-100 transition-opacity focus-within:opacity-100">
                  <button
                    type="button"
                    class="inline-flex items-center rounded-lg p-2 text-gray-400 hover:bg-red-50 hover:text-red-600 transition-colors disabled:opacity-50"
                    :disabled="isDeletingHistory"
                    title="删除记录"
                    @click.stop="openDeleteHistoryDialog(record.conversation_id, getHistoryRecordTitle(record))"
                  >
                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>

        <template v-else>
          <div v-if="showHistoryPanel" class="history-overlay" @click="showHistoryPanel = false" />

          <aside class="history-rail history-rail--drawer flex flex-col bg-white border-r border-gray-100 lg:shadow-none" :class="{ open: showHistoryPanel }">
            <div class="flex items-center justify-between p-5 border-b border-gray-50 bg-gray-50/30 shrink-0">
              <div>
                <span class="inline-flex items-center rounded-md bg-purple-50 px-2 py-1 text-xs font-medium text-purple-700 ring-1 ring-inset ring-purple-700/10 mb-1.5">
                  History
                </span>
                <h3 class="text-base font-semibold text-gray-900 tracking-tight">备课历史</h3>
              </div>
              <button 
                type="button" 
                class="rounded-lg p-2 text-gray-400 hover:bg-white hover:text-gray-600 hover:shadow-sm border border-transparent hover:border-gray-200 transition-all focus:outline-none focus:ring-2 focus:ring-purple-500"
                @click="fetchHistoryRecords"
                title="刷新"
              >
                <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" /></svg>
              </button>
            </div>

            <div class="flex-1 overflow-y-auto custom-scrollbar p-3 space-y-2">
              <div v-if="isLoadingHistory" class="flex flex-col items-center justify-center py-10">
                <div class="relative h-6 w-6">
                  <div class="absolute inset-0 rounded-full border-2 border-purple-100"></div>
                  <div class="absolute inset-0 animate-spin rounded-full border-2 border-purple-600 border-t-transparent"></div>
                </div>
                <p class="mt-3 text-xs text-gray-500">加载中...</p>
              </div>
              
              <div v-else-if="historyRecords.length === 0" class="flex flex-col items-center justify-center py-10">
                <svg class="h-8 w-8 text-gray-300 mb-2" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" /></svg>
                <p class="text-xs text-gray-500">暂无备课历史</p>
              </div>
              
              <template v-else>
                <div
                  v-for="record in historyRecords"
                  :key="record.conversation_id"
                  class="group relative flex flex-col rounded-xl border p-3 transition-all cursor-pointer"
                  :class="selectedHistoryId === record.conversation_id ? 'border-purple-200 bg-purple-50/50 shadow-sm' : 'border-transparent hover:border-gray-200 hover:bg-gray-50'"
                  @click="loadHistoryRecord(record.conversation_id)"
                >
                  <div class="flex items-start justify-between gap-2">
                    <h4 
                      class="text-sm font-medium line-clamp-2 leading-snug"
                      :class="selectedHistoryId === record.conversation_id ? 'text-purple-900' : 'text-gray-700 group-hover:text-gray-900'"
                    >
                      {{ getHistoryRecordTitle(record) }}
                    </h4>
                    <button
                      type="button"
                      class="shrink-0 rounded p-1 text-gray-300 opacity-0 transition-all hover:bg-red-50 hover:text-red-500 group-hover:opacity-100 focus:opacity-100"
                      :disabled="isDeletingHistory"
                      title="删除"
                      @click.stop="openDeleteHistoryDialog(record.conversation_id, getHistoryRecordTitle(record))"
                    >
                      <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" /></svg>
                    </button>
                  </div>
                  <div class="mt-2 flex items-center justify-between text-xs">
                    <span class="font-mono text-gray-400" :class="selectedHistoryId === record.conversation_id ? 'text-purple-400' : ''">ID: {{ record.conversation_id.substring(0, 6) }}</span>
                    <span v-if="record.created_at" class="text-gray-400" :class="selectedHistoryId === record.conversation_id ? 'text-purple-400' : ''">{{ new Date(record.created_at).toLocaleDateString('zh-CN') }}</span>
                  </div>
                </div>
              </template>
            </div>
          </aside>

          <section class="result-grid result-grid--breakout result-grid--preview">
            <aside class="result-format-rail history-preview-rail">
              <button
                v-for="tab in availablePreviewTabs"
                :key="tab.key"
                type="button"
                class="result-format-button result-format-button--history"
                :class="{ active: previewTab === tab.key, ready: true }"
                @click="previewTab = tab.key"
              >
                <span class="result-format-label">{{ tab.label }}</span>
                <span class="result-format-meta">历史预览</span>
              </button>
            </aside>

            <div class="result-main-panel result-main-panel--preview">
              <div class="result-preview-shell">
                <div class="result-preview-toolbar">
                <div class="result-preview-toolbar-copy">
                  <span class="summary-kicker">Preview</span>
                  <h3>{{ historyPreviewTitle }}</h3>
                  <p>{{ historyPreviewDescription }}</p>
                </div>

                <div class="result-preview-toolbar-actions">
                  <select
                    v-if="historyDetailUsesThemeSelect"
                    v-model="selectedPptTheme"
                    class="planner-select compact-select result-theme-select"
                  >
                    <option value="auto">模板：自动</option>
                    <option value="clean">模板：clean</option>
                    <option value="tech">模板：tech</option>
                    <option value="vivid">模板：vivid</option>
                  </select>

                  <button
                    v-if="historyDetailExportLabel"
                    type="button"
                    class="planner-export-button"
                    :disabled="historyDetailExporting || !lessonPlanSpec"
                    @click="exportHistoryDetailAsset"
                  >
                    {{ historyDetailExportLabel }}
                  </button>

                  <button
                    v-if="historyDetailCanDownload"
                    type="button"
                    class="planner-ghost-button"
                    @click="downloadHistoryDetailAsset"
                  >
                    下载文件
                  </button>
                </div>
              </div>

                <div v-if="isGenerating" class="result-empty-state">
                  <div class="spinner" />
                  <p>正在生成备课内容，请稍候...</p>
                </div>
                <div v-else-if="lessonPlanContent || lessonPlanSpec" class="result-preview-body result-preview-body--history">
                  <div v-if="previewTab === 'markdown'" class="result-markdown-preview">
                    <MarkdownViewer :content="lessonPlanContent" />
                  </div>
                  <div v-else-if="previewTab === 'summary'" class="history-preview-content">
                    <template v-if="previewTab === 'summary' && lessonPlanSpec">
                      <div class="summary-preview-grid">
                        <article class="preview-mini-card">
                          <h4>基础信息</h4>
                          <p>主题：{{ lessonPlanSpec.requirement_summary.topic || '未填写' }}</p>
                          <p>课程：{{ getCourseNameById(formData.courseId) || '未填写' }}</p>
                          <p>章节：{{ lessonPlanSpec.requirement_summary.chapter_title || '未填写' }}</p>
                          <p>学段 / 年级 / 学科：{{ lessonPlanSpec.requirement_summary.grade_subject || '未填写' }}</p>
                          <p>课时长度：{{ lessonPlanSpec.requirement_summary.duration || '未填写' }}</p>
                        </article>
                        <article class="preview-mini-card">
                          <h4>教学要求</h4>
                          <p>目标：{{ lessonPlanSpec.requirement_summary.teaching_goals.join('；') || '未填写' }}</p>
                          <p>重点：{{ lessonPlanSpec.requirement_summary.key_points.join('；') || '未填写' }}</p>
                          <p>难点：{{ lessonPlanSpec.requirement_summary.difficult_points.join('；') || '未填写' }}</p>
                          <p>风格：{{ lessonPlanSpec.requirement_summary.style.teaching_style || '未填写' }}</p>
                        </article>
                      </div>
                    </template>
                  </div>
                  <div v-else-if="previewTab === 'game' && historyGameMaterialUrl" class="result-link-preview-wrapper">
                    <div class="game-link-card">
                      <div class="game-link-icon">🎮</div>
                      <div class="game-link-content">
                        <h3 class="game-link-title">互动小游戏链接已生成</h3>
                        <p class="game-link-desc">您可以点击下方按钮直接访问，或复制链接分享给学生。</p>
                        <div class="game-link-actions">
                          <button type="button" class="planner-ghost-button" @click="copyLinkToClipboard(historyGameMaterialUrl)">
                            📋 复制链接
                          </button>
                          <a :href="historyGameMaterialUrl" target="_blank" rel="noopener noreferrer" class="planner-primary-button" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 6px;">
                            🌐 点击访问
                          </a>
                        </div>
                      </div>
                    </div>
                  </div>
                  <div
                    v-else-if="historyDetailAssetKey !== 'markdown' && historyDetailAssetKey !== 'game' && historyDetailMaterialId && formData.courseId"
                    class="result-material-preview"
                  >
                    <MaterialPreview
                      :course-id="Number(formData.courseId)"
                      :initial-material-id="historyDetailMaterialId"
                      :hide-back-button="true"
                      :hide-sidebar="true"
                      :hide-preview-header="true"
                    />
                  </div>
                  <div v-else class="result-empty-state result-empty-state--blank">
                    <p>{{ historyPreviewEmptyHint }}</p>
                  </div>

                  <div v-if="sources.length > 0" class="sources-strip">
                    <h4>参考来源</h4>
                    <ul>
                      <li v-for="(source, index) in sources" :key="`${source.title}-${index}`">{{ source.title }}</li>
                    </ul>
                  </div>
                </div>
                <div v-else class="result-empty-state">
                  <p>请选择一条历史记录，或返回入口新建备课。</p>
                </div>
              </div>
            </div>

            <aside class="result-side-panel">
              <section class="summary-card">
                <h4>当前需求</h4>
                <div v-if="lessonPlanSpec" class="summary-grid">
                  <div>
                    <dt>主题</dt>
                    <dd>{{ lessonPlanSpec.requirement_summary.topic || '未填写' }}</dd>
                  </div>
                  <div>
                    <dt>学情</dt>
                    <dd>{{ lessonPlanSpec.requirement_summary.student_profile.foundation || activeStudentLevelText || '未填写' }}</dd>
                  </div>
                  <div>
                    <dt>产出</dt>
                    <dd>{{ deliverableSummaryText }}</dd>
                  </div>
                  <div>
                    <dt>课堂类型</dt>
                    <dd>{{ requirementDraft.activities.join('、') || '未填写' }}</dd>
                  </div>
                </div>
                <p v-else class="summary-empty">暂无已加载的备课结果。</p>
              </section>

              <section class="summary-card">
                <div class="card-head-inline">
                  <h4>版本列表</h4>
                  <span class="mini-note">点击回退旧版</span>
                </div>
                <div v-if="lessonPlanVersions.length === 0" class="summary-empty">暂无结构化版本。</div>
                <div v-else class="version-list">
                  <button
                    v-for="version in lessonPlanVersions"
                    :key="version.version_index"
                    type="button"
                    class="version-card"
                    :class="{ active: selectedVersionIndex === version.version_index }"
                    @click="selectLessonPlanVersion(version.version_index)"
                  >
                    <strong>V{{ version.version_index }}</strong>
                    <span>{{ formatDate(version.revision_meta.created_at) }}</span>
                    <small>{{ version.revision_meta.revision_request || '初始生成' }}</small>
                  </button>
                </div>
              </section>

              <section class="summary-card">
                <div class="card-head-inline">
                  <h4>修改意见</h4>
                  <span class="mini-note">基于当前版本增量修订</span>
                </div>
                <div class="shortcut-row">
                  <button type="button" class="hint-chip" @click="applyRevisionShortcut('调整顺序')">调整顺序</button>
                  <button type="button" class="hint-chip" @click="applyRevisionShortcut('简化内容')">简化内容</button>
                  <button type="button" class="hint-chip" @click="applyRevisionShortcut('增加案例')">增加案例</button>
                  <button type="button" class="hint-chip" @click="applyRevisionShortcut('改成探究式')">改成探究式</button>
                </div>
                <textarea v-model="revisionRequest" rows="5" class="planner-textarea compact-textarea" placeholder="例如：把案例放到第 3 页，压缩定义讲解，增加一个贴近生活的例子。" :disabled="!canReviseCurrentLessonPlan" />
                <button type="button" class="planner-primary-button full-width" :disabled="!canReviseCurrentLessonPlan || !revisionRequest.trim()" @click="reviseLessonPlan">
                  {{ isRevisingLessonPlan ? '重新生成中...' : '重新生成' }}
                </button>
                <p v-if="!canReviseCurrentLessonPlan" class="summary-empty">只有结构化备课版本支持增量修订。</p>
              </section>
            </aside>
          </section>
        </template>
      </section>

      <section v-else class="result-grid result-grid--breakout result-grid--preview">
        <aside class="result-format-rail">
          <button
            v-for="option in resultAssetOptions"
            :key="option.key"
            type="button"
            class="result-format-button"
            :class="[
              `result-format-button--${option.accent || option.key}`,
              { active: activeResultAsset === option.key, ready: option.ready }
            ]"
            @click="activeResultAsset = option.key"
          >
            <span class="result-format-label">{{ option.label }}</span>
            <span class="result-format-meta">{{ option.ready ? '已生成' : '待生成' }}</span>
          </button>
        </aside>

        <div class="result-main-panel result-main-panel--preview">
          <div class="result-preview-shell">
            <div class="result-preview-toolbar">
              <div class="result-preview-toolbar-copy">
                <span class="summary-kicker">Preview</span>
                <h3>{{ activeResultAssetLabel }}</h3>
                <p v-if="activeResultAsset === 'markdown'">
                  当前显示结构化备课的 Markdown 版本，可直接在这里预览并导出。
                </p>
                <p v-else-if="activeResultAsset === 'game'">
                  互动小游戏已生成。这里不再内嵌预览，点击下方链接即可在新页面打开。
                </p>
                <p v-else-if="canPreviewActiveResult">
                  当前文件已生成，下面直接复用课程资源预览界面进行在线预览。
                </p>
                <p v-else>
                  当前文件还没有生成，点击右侧按钮后会在这里直接出现预览。
                </p>
              </div>

              <div class="result-preview-toolbar-actions">
                <select
                  v-if="activeResultAsset === 'ppt' || activeResultAsset === 'game'"
                  v-model="selectedPptTheme"
                  class="planner-select compact-select result-theme-select"
                >
                  <option value="auto">模板：自动</option>
                  <option value="clean">模板：clean</option>
                  <option value="tech">模板：tech</option>
                  <option value="vivid">模板：vivid</option>
                </select>

                <button
                  type="button"
                  class="planner-export-button"
                  :disabled="activeResultExporting || (!lessonPlanSpec && activeResultAsset !== 'markdown')"
                  @click="exportActiveResultAsset"
                >
                  {{ activeResultExportLabel }}
                </button>

                <button
                  v-if="canDownloadActiveResult && activeResultAsset !== 'markdown'"
                  type="button"
                  class="planner-ghost-button"
                  @click="downloadActiveResult"
                >
                  下载文件
                </button>
              </div>
            </div>

            <div v-if="showResultExportProgress" class="result-progress-slot">
              <div class="generation-progress-card generation-progress-card--embedded">
                <div class="generation-progress-copy">
                  <strong>{{ activeProgressTask?.label }}</strong>
                  <span>{{ activeProgressTask?.detail }}</span>
                </div>
                <div class="generation-progress-track" aria-hidden="true">
                  <span class="generation-progress-fill" :style="{ width: `${displayProgressPercent}%` }" />
                </div>
                <div class="generation-progress-meta">
                  <span>处理中</span>
                  <strong>{{ displayProgressPercent }}%</strong>
                </div>
              </div>
            </div>

            <div class="result-preview-body">
              <div v-if="isGenerating" class="result-empty-state">
                <div class="spinner" />
                <p>正在生成备课内容，请稍候...</p>
              </div>

              <div v-else-if="activeResultAsset === 'markdown' && lessonPlanContent" class="result-markdown-preview">
                <MarkdownViewer :content="lessonPlanContent" />
              </div>

              <div v-else-if="activeResultAsset === 'game' && activeGameMaterialUrl" class="result-link-preview-wrapper">
                <div class="game-link-card">
                  <div class="game-link-icon">🎮</div>
                  <div class="game-link-content">
                    <h3 class="game-link-title">互动小游戏链接已生成</h3>
                    <p class="game-link-desc">您可以点击下方按钮直接访问，或复制链接分享给学生。</p>
                    <div class="game-link-actions">
                      <button type="button" class="planner-ghost-button" @click="copyLinkToClipboard(activeGameMaterialUrl)">
                        📋 复制链接
                      </button>
                      <a :href="activeGameMaterialUrl" target="_blank" rel="noopener noreferrer" class="planner-primary-button" style="text-decoration: none; display: inline-flex; align-items: center; justify-content: center; gap: 6px;">
                        🌐 点击访问
                      </a>
                    </div>
                  </div>
                </div>
              </div>

              <div
                v-else-if="activeResultAsset !== 'markdown' && activeResultAsset !== 'game' && canPreviewActiveResult && formData.courseId"
                class="result-material-preview"
              >
                <MaterialPreview
                  :course-id="Number(formData.courseId)"
                  :initial-material-id="activeResultMaterialId"
                  :hide-back-button="true"
                  :hide-sidebar="true"
                  :hide-preview-header="true"
                />
              </div>

              <div v-else-if="lessonPlanSpec || lessonPlanContent" class="result-empty-state result-empty-state--blank" />

              <div v-else class="result-empty-state">
                <p>请先完成上一页需求确认，再进入结果页预览生成内容。</p>
              </div>
            </div>
          </div>
        </div>

        <aside class="result-side-panel">
          <section class="summary-card">
            <h4>当前需求</h4>
            <div v-if="lessonPlanSpec" class="summary-grid">
              <div>
                <dt>主题</dt>
                <dd>{{ lessonPlanSpec.requirement_summary.topic || '未填写' }}</dd>
              </div>
              <div>
                <dt>学情</dt>
                <dd>{{ lessonPlanSpec.requirement_summary.student_profile.foundation || activeStudentLevelText || '未填写' }}</dd>
              </div>
              <div>
                <dt>产出</dt>
                <dd>{{ deliverableSummaryText }}</dd>
              </div>
              <div>
                <dt>课堂类型</dt>
                <dd>{{ requirementDraft.activities.join('、') || '未填写' }}</dd>
              </div>
            </div>
            <p v-else class="summary-empty">暂无已加载的备课结果。</p>
          </section>

          <section class="summary-card">
            <div class="card-head-inline">
              <h4>版本列表</h4>
              <span class="mini-note">点击回退旧版</span>
            </div>
            <div v-if="lessonPlanVersions.length === 0" class="summary-empty">暂无结构化版本。</div>
            <div v-else class="version-list">
              <button
                v-for="version in lessonPlanVersions"
                :key="version.version_index"
                type="button"
                class="version-card"
                :class="{ active: selectedVersionIndex === version.version_index }"
                @click="selectLessonPlanVersion(version.version_index)"
              >
                <strong>V{{ version.version_index }}</strong>
                <span>{{ formatDate(version.revision_meta.created_at) }}</span>
                <small>{{ version.revision_meta.revision_request || '初始生成' }}</small>
              </button>
            </div>
          </section>

          <section class="summary-card">
            <div class="card-head-inline">
              <h4>修改意见</h4>
              <span class="mini-note">基于当前版本增量修订</span>
            </div>
            <div class="shortcut-row">
              <button type="button" class="hint-chip" @click="applyRevisionShortcut('调整顺序')">调整顺序</button>
              <button type="button" class="hint-chip" @click="applyRevisionShortcut('简化内容')">简化内容</button>
              <button type="button" class="hint-chip" @click="applyRevisionShortcut('增加案例')">增加案例</button>
              <button type="button" class="hint-chip" @click="applyRevisionShortcut('改成探究式')">改成探究式</button>
            </div>
            <textarea
              v-model="revisionRequest"
              rows="5"
              class="planner-textarea compact-textarea"
              placeholder="例如：把案例放到第 3 页，压缩定义讲解，增加一个贴近生活的例子。"
              :disabled="!canReviseCurrentLessonPlan"
            />
            <div v-if="showRevisionProgress" class="generation-progress-card generation-progress-card--compact">
              <div class="generation-progress-copy">
                <strong>{{ activeProgressTask?.label }}</strong>
                <span>{{ activeProgressTask?.detail }}</span>
              </div>
              <div class="generation-progress-track" aria-hidden="true">
                <span class="generation-progress-fill" :style="{ width: `${displayProgressPercent}%` }" />
              </div>
              <div class="generation-progress-meta">
                <span>处理中</span>
                <strong>{{ displayProgressPercent }}%</strong>
              </div>
            </div>
            <button type="button" class="planner-primary-button full-width" :disabled="!canReviseCurrentLessonPlan || !revisionRequest.trim()" @click="reviseLessonPlan">
              {{ isRevisingLessonPlan ? '重新生成中...' : '重新生成' }}
            </button>
            <p v-if="!canReviseCurrentLessonPlan" class="summary-empty">只有结构化备课版本支持增量修订。</p>
          </section>
        </aside>
      </section>
    </div>
  </div>

  <div v-if="pendingDeleteHistory" class="fixed inset-0 z-[100] flex items-center justify-center bg-black/40 backdrop-blur-sm transition-opacity" @click="closeDeleteHistoryDialog">
    <div class="relative w-full max-w-md transform overflow-hidden rounded-2xl bg-white text-left align-middle shadow-2xl transition-all" @click.stop>
      <div class="px-6 py-6 border-b border-gray-50 flex items-start gap-4">
        <div class="mx-auto flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-red-50 sm:mx-0 sm:h-10 sm:w-10">
          <svg class="h-5 w-5 text-red-600" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" /></svg>
        </div>
        <div class="mt-1 flex-1">
          <h3 class="text-base font-semibold leading-6 text-gray-900">彻底删除备课历史</h3>
          <p class="mt-2 text-sm text-gray-500">删除后，这条备课历史会从前端列表和后台记录里一起清掉，此操作不可撤销。</p>
          
          <div class="mt-4 rounded-xl bg-gray-50 p-4 border border-gray-100">
            <p class="text-xs font-medium text-gray-500 mb-1">将删除的记录</p>
            <p class="text-sm font-medium text-gray-900 line-clamp-2">{{ pendingDeleteHistory.title }}</p>
          </div>
        </div>
        
        <button 
          type="button" 
          class="absolute top-4 right-4 rounded-md text-gray-400 hover:text-gray-500 hover:bg-gray-100 p-1 transition-colors focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2" 
          :disabled="isDeletingHistory" 
          @click="closeDeleteHistoryDialog"
        >
          <span class="sr-only">关闭</span>
          <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
        </button>
      </div>

      <div class="bg-gray-50/50 px-6 py-4 flex items-center justify-end gap-3">
        <button 
          type="button" 
          class="inline-flex justify-center rounded-lg border border-gray-200 bg-white px-4 py-2.5 text-sm font-medium text-gray-700 shadow-sm hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-gray-200 transition-colors disabled:opacity-50" 
          :disabled="isDeletingHistory" 
          @click="closeDeleteHistoryDialog"
        >
          取消
        </button>
        <button 
          type="button" 
          class="inline-flex justify-center rounded-lg bg-red-600 px-4 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2 transition-colors disabled:opacity-50" 
          :disabled="isDeletingHistory" 
          @click="confirmDeleteHistory"
        >
          <svg v-if="isDeletingHistory" class="animate-spin -ml-1 mr-2 h-4 w-4 text-white" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
          {{ isDeletingHistory ? '删除中...' : '彻底删除' }}
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import {
  courseAPI,
  knowledgeBaseAPI,
  materialAPI,
  ragAiAPI,
  type GenerateLessonPptTheme,
  type KnowledgeBaseStatusItem,
  type LessonPlanGenerateResponse,
  type LessonPlanSourceItem,
  type LessonPlanSpec,
  type LessonPlanSpecGamePlan,
  type LessonPlanStoredPayload,
  type ProcessedSource,
  type RevisionMeta,
  type ReviseLessonPlanResponse,
  type SourceUsage,
} from '../../api';
import MarkdownViewer from '../course/MarkdownViewer.vue';
import { useAudioTranscription } from '@/composables/useAudioTranscription';
import MaterialPreview from '../course/MaterialPreview.vue';
import { useAuthStore } from '@/stores/auth';
import notificationService from '@/services/notificationService';
import {
  LESSON_PLANNER_DRAFT_KEY,
  LESSON_PLANNER_RESULT_KEY,
  LESSON_PLANNER_CONVERSATION_KEY,
  LESSON_PLANNER_STRUCTURED_KEY,
  LESSON_PLANNER_GAME_EXPORT_KEY,
  clearLessonPlannerStorage
} from '@/utils/lessonPlannerStorage';
import { API_BASE_URL, API_ORIGIN } from '@/config/api';

const props = withDefaults(defineProps<{
  hideHeader?: boolean;
  headerTarget?: string;
  scrollAnchorTarget?: string;
}>(), {
  hideHeader: false,
  headerTarget: '',
  scrollAnchorTarget: ''
});

const authStore = useAuthStore();

type EntryMode = 'launcher' | 'create' | 'history' | 'result';
type WizardStep = 1 | 2 | 3 | 4;
type Deliverable = 'word' | 'ppt' | 'game';
type PreviewTab = 'summary' | 'ppt' | 'docx' | 'game' | 'markdown';
type ResultAssetKey = 'word' | 'ppt' | 'game' | 'markdown';
type ProgressTaskKey = 'lesson' | 'word' | 'ppt' | 'game' | 'revise';

interface Course {
  id: number;
  name: string;
}

interface Chapter {
  id: number;
  title: string;
}

interface HistoryRecord {
  conversation_id: string;
  title: string;
  display_title?: string;
  course_id?: number | null;
  chapter_id?: string;
  created_at?: number | string;
  start_time: number;
  last_time: number;
  outline_type: 'course' | 'class';
  message_count: number;
  subject?: string;
  grade?: string;
  chapter_title?: string;
  topic?: string;
}

interface HistoryMessage {
  role: string;
  content: string;
  timestamp: number;
}

interface RequirementSummary {
  teaching_goals: string[];
  knowledge_points: string[];
  duration: string;
  style: string;
  output_targets: string[];
}

interface TeachingFlowStep {
  step: number;
  title: string;
  goal: string;
}

interface StructuredRequirement {
  topic: string;
  knowledge_points: string[];
  teaching_flow: TeachingFlowStep[];
  key_points: string[];
  difficult_points: string[];
  student_profile: {
    grade: string;
    foundation: string;
    learning_preference: string;
  };
  style: {
    teaching_style: string;
    interaction_level: string;
    output_preference: string;
  };
}

interface SourceItem {
  title: string;
  url: string;
  purpose?: string;
  mapping?: {
    usage: SourceUsage;
    knowledge_point: string;
    is_required: boolean;
  };
}

interface UploadedFile {
  clientId: string;
  name: string;
  path: string;
  hash: string;
  size: number;
  usage: string;
  knowledgePoint: string;
  isRequired: boolean | null;
  status: 'uploading' | 'ready' | 'failed';
  progress: number;
  errorMessage?: string;
}

interface LessonPlanVersion {
  version_index: number;
  lesson_plan_spec: LessonPlanSpec;
  core_spec?: Record<string, any> | null;
  sources: SourceItem[];
  revision_meta: RevisionMeta;
  generated_assets?: {
    word?: number | null;
    ppt?: number | null;
    game?: number | null;
  };
  timestamp: number;
}

interface GradeDraft {
  stage: string;
  grade: string;
  subject: string;
}

interface RequirementDraft {
  duration: string;
  objectives: string;
  keyPoints: string;
  difficultPoints: string;
  teachingStyle: string;
  studentPreset: string;
  customStudentPreset: string;
  detailLevel: number;
  activities: string[];
  freeTeachingIdea: string;
}

interface ChatTurn {
  role: 'assistant' | 'user';
  content: string;
  timestamp: number;
  requirementChecklist?: Array<{
    key: string;
    label: string;
    detail: string;
    status: 'done' | 'pending';
  }>;
  followupQuestion?: string;
  quickPrompts?: string[];
}

interface StoredLessonPlanSpecPayload extends LessonPlanStoredPayload {
  sources?: LessonPlanSourceItem[];
  core_spec?: Record<string, any>;
  generated_assets?: {
    word?: number | null;
    ppt?: number | null;
    game?: number | null;
  };
}

interface GameHtmlExportCache {
  courseId: number;
  materialId: number;
  title?: string;
}

interface FormDataState {
  courseId: string;
  outlineType: 'class' | 'course';
  chapterId: string;
  gradeSubject: string;
  duration: string;
  learningObjectives: string;
  keyPoints: string;
  studentLevel: string;
  customStudentLevel: string;
  activities: string[];
  teachingStyle: string;
  assessmentMethods: string[];
  detailLevel: number;
  freeTeachingIdea: string;
  useKnowledgeBase: boolean;
}

const stepItems = [
  { index: 0, label: '入口' },
  { index: 1, label: '课程与章节' },
  { index: 2, label: '选择资源' },
  { index: 3, label: '确认需求' },
  { index: 4, label: '生成结果' }
] as const;

const deliveryOptions: Array<{ value: Deliverable; label: string; description: string }> = [
  { value: 'word', label: 'Word 教案', description: '输出可导出的文字教案结构。' },
  { value: 'ppt', label: 'PPT 课件', description: '生成适合课堂展示的页面大纲。' },
  { value: 'game', label: '互动小游戏', description: '生成 HTML5 闯关方案，并自动包含 PPT。' }
];

const sourceUsageOptions: Array<{ value: SourceUsage; label: string }> = [
  { value: 'content', label: '用于内容' },
  { value: 'format', label: '用于格式' },
  { value: 'case', label: '用于案例' },
  { value: 'image_asset', label: '用于图片素材' }
];

const studentPresetOptions = ['基础薄弱', '中等水平', '较高水平', '自定义'];
const activityOptions = ['小组讨论', '实验', '角色扮演', '游戏辩论', '演讲', '练习测验'];
const teachingStyleOptions = ['讲授型', '探究式', '项目式', '合作学习', '翻转课堂'];
const ideaHints = ['课堂节奏怎么安排？', '学生基础是什么水平？', '想用什么案例或情境？', '教学重点和难点是什么？', '希望有哪些互动活动？'];
const defaultAssistantPrompt = '您好。为了把这节课备得更贴合您的想法，先告诉我这节课的大致设想。您可以先说课堂节奏、案例情境、学生基础、教学目标、重点难点或者互动方式；您先随意讲，我会边听边提取要点，并在不清楚的地方继续追问。';
const defaultGradeDraft: GradeDraft = { stage: '高中', grade: '高一', subject: '数学' };
const MAX_TEMP_UPLOAD_SIZE_BYTES = 200 * 1024 * 1024;
const DEFAULT_TEMP_UPLOAD_TIMEOUT_MS = 5 * 60 * 1000;
const VIDEO_TEMP_UPLOAD_TIMEOUT_MS = 15 * 60 * 1000;
const VIDEO_FILE_EXTENSIONS = new Set(['mp4', 'mov', 'avi', 'mkv', 'webm']);

const entryMode = ref<EntryMode>('launcher');
const wizardStep = ref<WizardStep>(1);
const plannerShellRef = ref<HTMLElement | null>(null);
const showHistoryPanel = ref(false);
const showSummaryPanel = ref(true);
const pendingDeleteHistory = ref<{ conversationId: string; title: string } | null>(null);
const isDeletingHistory = ref(false);

const courses = ref<Course[]>([]);
const chapters = ref<Chapter[]>([]);
const knowledgeItems = ref<KnowledgeBaseStatusItem[]>([]);
const historyRecords = ref<HistoryRecord[]>([]);

const deliverables = ref<Deliverable[]>(['word', 'ppt']);
const gradeDraft = ref<GradeDraft>({ ...defaultGradeDraft });
const selectedKnowledgeItems = ref<KnowledgeBaseStatusItem[]>([]);
const uploadedFiles = ref<UploadedFile[]>([]);
const processedSources = ref<ProcessedSource[]>([]);
const processedSourcesHash = ref('');
const processedSourcesDirty = ref(false);
const resourceStepAttempted = ref(false);

const requirementDraft = ref<RequirementDraft>({
  duration: '',
  objectives: '',
  keyPoints: '',
  difficultPoints: '',
  teachingStyle: '',
  studentPreset: '中等水平',
  customStudentPreset: '',
  detailLevel: 2,
  activities: [],
  freeTeachingIdea: ''
});

const chatDraft = ref('');
const chatThreadContainer = ref<HTMLElement | null>(null);
const chatTranscript = ref<ChatTurn[]>([]);
const missingFields = ref<string[]>([]);
const followupPrompts = ref<string[]>([]);
const requirementSummary = ref<RequirementSummary | null>(null);
const structuredRequirement = ref<StructuredRequirement | null>(null);

const lessonPlanContent = ref('');
const lessonPlanSpec = ref<LessonPlanSpec | null>(null);
const sources = ref<SourceItem[]>([]);
const lessonPlanVersions = ref<LessonPlanVersion[]>([]);
const selectedVersionIndex = ref<number | null>(null);
const selectedHistoryId = ref('');
const currentConversationId = ref('');
const revisionRequest = ref('');
const latestGameHtmlExport = ref<GameHtmlExportCache | null>(null);
const generatedResultMaterials = ref<{ word: number | null; ppt: number | null; game: number | null }>({
  word: null,
  ppt: null,
  game: null
});

const selectedPptTheme = ref<'auto' | GenerateLessonPptTheme>('auto');
const previewTab = ref<PreviewTab>('summary');
const activeResultAsset = ref<ResultAssetKey>('ppt');
const knowledgePickerOpen = ref(false);
const knowledgeSearchQuery = ref('');

const formData = ref<FormDataState>({
  courseId: '',
  outlineType: 'class',
  chapterId: '',
  gradeSubject: '',
  duration: '',
  learningObjectives: '',
  keyPoints: '',
  studentLevel: '中等水平',
  customStudentLevel: '',
  activities: [],
  teachingStyle: '',
  assessmentMethods: [],
  detailLevel: 2,
  freeTeachingIdea: '',
  useKnowledgeBase: false
});

const isLoadingHistory = ref(false);
const isGenerating = ref(false);
const isGeneratingPpt = ref(false);
const isGeneratingDocx = ref(false);
const isGeneratingGameHtml = ref(false);
const isPreparingGameHtmlForPpt = ref(false);
const isRevisingLessonPlan = ref(false);
const isSummarizingRequirement = ref(false);
const isStructuringRequirement = ref(false);
const isProcessingSources = ref(false);
const progressPercent = ref(0);
const uploadControllers = new Map<string, AbortController>();
let progressTimer: number | null = null;
let progressResetTimer: number | null = null;
let progressTaskStartedAt = 0;
let progressTaskKey: ProgressTaskKey | null = null;

const {
  isRecording,
  isTranscribing,
  startRecording,
  stopRecording,
} = useAudioTranscription({
  filePrefix: 'lesson_idea',
  onTranscribed: (text) => {
    chatDraft.value = chatDraft.value ? `${chatDraft.value}\n${text}` : text;
  },
  onError: (message, error) => {
    console.error(message, error);
    alert(message);
  }
});

const progressTaskDurations: Record<ProgressTaskKey, number> = {
  lesson: 120000,
  revise: 90000,
  ppt: 70000,
  word: 60000,
  game: 50000,
};

const progressTaskMilestones: Record<ProgressTaskKey, Array<{ ratio: number; percent: number }>> = {
  lesson: [
    { ratio: 0, percent: 6 },
    { ratio: 0.12, percent: 12 },
    { ratio: 0.28, percent: 24 },
    { ratio: 0.5, percent: 46 },
    { ratio: 0.7, percent: 64 },
    { ratio: 0.86, percent: 78 },
    { ratio: 1, percent: 90 },
    { ratio: 1.18, percent: 94 },
    { ratio: 1.45, percent: 97 },
  ],
  revise: [
    { ratio: 0, percent: 8 },
    { ratio: 0.16, percent: 18 },
    { ratio: 0.35, percent: 36 },
    { ratio: 0.58, percent: 58 },
    { ratio: 0.82, percent: 78 },
    { ratio: 1, percent: 90 },
    { ratio: 1.22, percent: 96 },
  ],
  ppt: [
    { ratio: 0, percent: 8 },
    { ratio: 0.18, percent: 20 },
    { ratio: 0.42, percent: 42 },
    { ratio: 0.68, percent: 66 },
    { ratio: 0.88, percent: 82 },
    { ratio: 1, percent: 90 },
    { ratio: 1.24, percent: 96 },
  ],
  word: [
    { ratio: 0, percent: 10 },
    { ratio: 0.18, percent: 24 },
    { ratio: 0.4, percent: 46 },
    { ratio: 0.66, percent: 68 },
    { ratio: 0.86, percent: 84 },
    { ratio: 1, percent: 91 },
    { ratio: 1.22, percent: 96 },
  ],
  game: [
    { ratio: 0, percent: 12 },
    { ratio: 0.18, percent: 26 },
    { ratio: 0.42, percent: 50 },
    { ratio: 0.66, percent: 72 },
    { ratio: 0.86, percent: 86 },
    { ratio: 1, percent: 92 },
    { ratio: 1.2, percent: 96 },
  ],
};

const currentStepIndex = computed(() => {
  if (entryMode.value === 'launcher') return 0;
  if (entryMode.value === 'create') return wizardStep.value;
  return 4;
});

const currentUserAvatarUrl = computed(() => String(authStore.user?.avatar_url || '').trim());
const currentUserAvatarInitial = computed(() => {
  const source = String(authStore.user?.full_name || authStore.user?.username || '我').trim();
  return source.charAt(0).toUpperCase() || '我';
});

function formatUserAvatarUrl(url: string) {
  if (!url) return '';
  if (url.startsWith('http')) return url;
  return `${API_ORIGIN}${url}`;
}

const compactFlowSteps = computed(() => stepItems.filter(item => item.index > 0));

const showTeleportedCompactBar = computed(() => (
  props.hideHeader &&
  !!props.headerTarget &&
  entryMode.value !== 'launcher'
));

const showInlineCompactBar = computed(() => (
  props.hideHeader &&
  !props.headerTarget &&
  entryMode.value !== 'launcher'
));

const showLocalHeader = computed(() => (
  !showTeleportedCompactBar.value &&
  (!props.hideHeader || entryMode.value !== 'launcher')
));

function resolvePlannerScrollAnchor() {
  if (props.scrollAnchorTarget) {
    const target = document.querySelector(props.scrollAnchorTarget);
    if (target instanceof HTMLElement) {
      return target;
    }
  }
  return plannerShellRef.value;
}

async function scrollPlannerToTop(behavior: ScrollBehavior = 'smooth') {
  await nextTick();
  const target = resolvePlannerScrollAnchor();
  if (!target) return;
  requestAnimationFrame(() => {
    target.scrollIntoView({ behavior, block: 'start' });
  });
}

const gradeSubjectText = computed(() => [gradeDraft.value.stage, gradeDraft.value.grade, gradeDraft.value.subject].filter(Boolean).join(' / '));
const deliverableSummaryText = computed(() => {
  if (deliverables.value.length === 0) return '未选择';
  return deliverables.value.map(value => deliveryOptions.find(item => item.value === value)?.label || value).join('、');
});

const readyUploadedFiles = computed(() =>
  uploadedFiles.value.filter(file => file.status === 'ready' && !!file.path)
);

const pendingUploadedFiles = computed(() =>
  uploadedFiles.value.filter(file => file.status === 'uploading')
);

const failedUploadedFiles = computed(() =>
  uploadedFiles.value.filter(file => file.status === 'failed')
);

const currentSourceProcessingHash = computed(() =>
  JSON.stringify(
    readyUploadedFiles.value.map(file => ({
      path: file.path,
      hash: file.hash,
      usage: file.usage || '',
      knowledgePoint: file.knowledgePoint.trim(),
      isRequired: file.isRequired
    }))
  )
);

const selectableKnowledgeItems = computed(() =>
  [...knowledgeItems.value]
    .filter(item => item.status === 'completed')
    .sort((left, right) => {
      if (left.purpose === 'lesson_plan' && right.purpose !== 'lesson_plan') return -1;
      if (left.purpose !== 'lesson_plan' && right.purpose === 'lesson_plan') return 1;
      return Number(right.created_at || 0) - Number(left.created_at || 0);
    })
);

const filteredKnowledgeOptions = computed(() => {
  const query = knowledgeSearchQuery.value.trim().toLowerCase();
  if (!query) return selectableKnowledgeItems.value;
  return selectableKnowledgeItems.value.filter(item => {
    const fileName = getFileName(item.file_path).toLowerCase();
    const purpose = getKnowledgePurposeLabel(item.purpose).toLowerCase();
    return fileName.includes(query) || purpose.includes(query);
  });
});

const knowledgePickerTriggerLabel = computed(() => {
  if (selectedKnowledgeItems.value.length > 0) {
    return `已选择 ${selectedKnowledgeItems.value.length} 份知识库文件`;
  }
  if (selectableKnowledgeItems.value.length === 0) {
    return '暂无可选知识库文件';
  }
  return '选择知识库文件';
});

const canMoveFromStepOne = computed(() =>
  Boolean(formData.value.courseId) &&
  Boolean(formData.value.chapterId) &&
  Boolean(gradeDraft.value.stage.trim()) &&
  Boolean(gradeDraft.value.grade.trim()) &&
  Boolean(gradeDraft.value.subject.trim()) &&
  deliverables.value.length > 0
);

const activeStudentLevelText = computed(() =>
  requirementDraft.value.studentPreset === '自定义'
    ? requirementDraft.value.customStudentPreset.trim()
    : requirementDraft.value.studentPreset
);

const canProcessSources = computed(() =>
  readyUploadedFiles.value.length > 0 &&
  pendingUploadedFiles.value.length === 0 &&
  failedUploadedFiles.value.length === 0 &&
  getInvalidSourceMappedFiles().length === 0 &&
  !isProcessingSources.value
);

const canMoveFromResourceStep = computed(() =>
  pendingUploadedFiles.value.length === 0 &&
  failedUploadedFiles.value.length === 0 &&
  getInvalidSourceMappedFiles().length === 0 &&
  getInvalidKnowledgeMappedItems().length === 0
);

const resourceStepGuideMessage = computed(() => {
  const parts: string[] = [];
  const invalidUploads = getInvalidSourceMappedFiles();
  const invalidKnowledge = getInvalidKnowledgeMappedItems();
  if (pendingUploadedFiles.value.length > 0) {
    parts.push(`仍有 ${pendingUploadedFiles.value.length} 个文件正在上传，请等待完成`);
  }
  if (failedUploadedFiles.value.length > 0) {
    parts.push(`有 ${failedUploadedFiles.value.length} 个文件上传失败，请删除后重新上传`);
  }
  if (readyUploadedFiles.value.length > 0 && invalidUploads.length === 0) {
    parts.push(`上传文件标注已完成 ${readyUploadedFiles.value.length} 项`);
  } else if (invalidUploads.length > 0) {
    parts.push(`上传文件还需补全 ${invalidUploads.length} 项：${invalidUploads.join('、')}`);
  }
  if (selectedKnowledgeItems.value.length > 0 && invalidKnowledge.length === 0) {
    parts.push(`知识库文件标注已完成 ${selectedKnowledgeItems.value.length} 项`);
  } else if (invalidKnowledge.length > 0) {
    parts.push(`知识库文件还需补全 ${invalidKnowledge.length} 项：${invalidKnowledge.join('、')}`);
  }
  if (parts.length === 0) {
    return '如果使用上传文件或知识库文件，请先为每份资料补全用途、关联知识点和是否必须参考。';
  }
  return parts.join('；');
});

const canGenerate = computed(() =>
  !isGenerating.value &&
  canMoveFromStepOne.value &&
  Boolean(requirementDraft.value.duration.trim()) &&
  Boolean(requirementDraft.value.objectives.trim())
);

const canReviseCurrentLessonPlan = computed(() =>
  !!lessonPlanSpec.value &&
  !!currentConversationId.value &&
  lessonPlanVersions.value.length > 0 &&
  !isRevisingLessonPlan.value
);

const currentGameHtmlMaterialId = computed(() => {
  const courseId = Number(formData.value.courseId || 0);
  if (!courseId || !latestGameHtmlExport.value) return null;
  if (latestGameHtmlExport.value.courseId !== courseId) return null;
  return latestGameHtmlExport.value.materialId;
});

const gameHtmlExportHint = computed(() => {
  if (!lessonPlanSpec.value || !showGameControl.value) return '';
  if (currentGameHtmlMaterialId.value) {
    return `已关联小游戏素材：${latestGameHtmlExport.value?.title || '小游戏 HTML'}`;
  }
  return '如需 PPT 内嵌小游戏入口，请先导出小游戏 HTML。';
});

const showPptControl = computed(() =>
  !!lessonPlanSpec.value && (
    entryMode.value === 'history' ||
    deliverables.value.includes('ppt') ||
    lessonPlanSpec.value.ppt_outline.length > 0
  )
);

const showWordControl = computed(() =>
  !!lessonPlanSpec.value && (
    entryMode.value === 'history' ||
    deliverables.value.includes('word') ||
    lessonPlanSpec.value.docx_outline.length > 0
  )
);

const showGameControl = computed(() =>
  !!lessonPlanSpec.value && (
    entryMode.value === 'history' ||
    deliverables.value.includes('game')
  )
);

const resultAssetOptions = computed<Array<{ key: ResultAssetKey; label: string; ready: boolean; accent?: string }>>(() => ([
  { key: 'word', label: 'Word 课件', ready: !!generatedResultMaterials.value.word, accent: 'word' },
  { key: 'ppt', label: 'PPTX 课件', ready: !!generatedResultMaterials.value.ppt, accent: 'ppt' },
  { key: 'game', label: '互动小游戏', ready: !!generatedResultMaterials.value.game || !!currentGameHtmlMaterialId.value, accent: 'game' },
  { key: 'markdown', label: 'Markdown', ready: !!lessonPlanContent.value, accent: 'markdown' }
]));

const activeResultMaterialId = computed(() => {
  if (activeResultAsset.value === 'markdown') return null;
  if (activeResultAsset.value === 'game') {
    return generatedResultMaterials.value.game || currentGameHtmlMaterialId.value;
  }
  return generatedResultMaterials.value[activeResultAsset.value];
});

function buildMaterialDownloadUrl(materialId: number | null): string {
  if (!materialId) return '';
  const token = localStorage.getItem('token');
  const baseUrl = `${API_BASE_URL}/materials/${materialId}/download`;
  return token ? `${baseUrl}?token=${encodeURIComponent(token)}` : baseUrl;
}

const activeGameMaterialUrl = computed(() =>
  activeResultAsset.value === 'game' ? buildMaterialDownloadUrl(activeResultMaterialId.value) : ''
);

const activeResultAssetLabel = computed(() =>
  resultAssetOptions.value.find(option => option.key === activeResultAsset.value)?.label || '当前文件'
);

const canPreviewActiveResult = computed(() =>
  activeResultAsset.value === 'markdown'
    ? !!lessonPlanContent.value
    : activeResultAsset.value === 'game'
      ? !!activeResultMaterialId.value
      : !!activeResultMaterialId.value && !!formData.value.courseId
);

const canDownloadActiveResult = computed(() =>
  activeResultAsset.value === 'markdown'
    ? !!lessonPlanContent.value
    : !!activeResultMaterialId.value
);

const activeResultExporting = computed(() => {
  if (activeResultAsset.value === 'word') return isGeneratingDocx.value;
  if (activeResultAsset.value === 'ppt') return isGeneratingPpt.value;
  if (activeResultAsset.value === 'game') return isGeneratingGameHtml.value;
  return false;
});

const activeProgressTask = computed<null | { key: 'lesson' | 'word' | 'ppt' | 'game' | 'revise'; label: string; detail: string }>(() => {
  if (isGenerating.value) {
    return {
      key: 'lesson',
      label: '正在生成备课内容',
      detail: '系统正在整理需求并生成结构化教案，请稍候。'
    };
  }
  if (isGeneratingDocx.value) {
    return {
      key: 'word',
      label: '正在生成 Word 课件',
      detail: '正在整理教案内容并导出 Word 文件。'
    };
  }
  if (isGeneratingPpt.value) {
    return {
      key: 'ppt',
      label: '正在生成 PPTX 课件',
      detail: '正在排版幻灯片内容并生成可预览文件。'
    };
  }
  if (isGeneratingGameHtml.value) {
    return {
      key: 'game',
      label: isPreparingGameHtmlForPpt.value ? '正在生成互动小游戏（PPT前置步骤）' : '正在生成互动小游戏',
      detail: isPreparingGameHtmlForPpt.value
        ? '已选择互动小游戏产出。PPT 需先拿到 HTML 链接，才能写入课后任务页与入口页，请稍候。'
        : '正在整理题目与页面素材并输出 HTML 文件。'
    };
  }
  if (isRevisingLessonPlan.value) {
    return {
      key: 'revise',
      label: '正在重新生成版本',
      detail: '系统正在基于当前修改意见重建备课版本。'
    };
  }
  return null;
});

const activeProgressTaskKey = computed(() => activeProgressTask.value?.key ?? null);

const showLessonGenerationProgress = computed(() => activeProgressTask.value?.key === 'lesson');
const showResultExportProgress = computed(() => ['word', 'ppt', 'game'].includes(activeProgressTask.value?.key ?? ''));
const showRevisionProgress = computed(() => activeProgressTask.value?.key === 'revise');

const copyLinkToClipboard = async (url: string) => {
  try {
    await navigator.clipboard.writeText(url);
    alert('小游戏链接已复制到剪贴板！');
  } catch (err) {
    alert('复制失败，请手动复制链接');
  }
};
const displayProgressPercent = computed(() => Math.max(0, Math.min(100, Math.round(progressPercent.value))));

const activeResultExportLabel = computed(() => {
  if (activeResultAsset.value === 'markdown') return '下载 Markdown';
  if (activeResultExporting.value) {
    if (activeResultAsset.value === 'word') return '生成中...';
    if (activeResultAsset.value === 'ppt') return '生成中...';
    return '导出中...';
  }
  if (activeResultAsset.value === 'word') return generatedResultMaterials.value.word ? '重新生成 Word' : '生成 Word';
  if (activeResultAsset.value === 'ppt') return generatedResultMaterials.value.ppt ? '重新生成 PPTX' : '生成 PPTX';
  return (generatedResultMaterials.value.game || currentGameHtmlMaterialId.value) ? '重新生成小游戏' : '生成小游戏';
});

const historyDetailAssetKey = computed<ResultAssetKey | null>(() => {
  if (previewTab.value === 'ppt') return 'ppt';
  if (previewTab.value === 'docx') return 'word';
  if (previewTab.value === 'game') return 'game';
  if (previewTab.value === 'markdown') return 'markdown';
  return null;
});

const historyDetailUsesThemeSelect = computed(() =>
  historyDetailAssetKey.value === 'ppt' || historyDetailAssetKey.value === 'game'
);

const historyDetailExporting = computed(() => {
  if (historyDetailAssetKey.value === 'word') return isGeneratingDocx.value;
  if (historyDetailAssetKey.value === 'ppt') return isGeneratingPpt.value;
  if (historyDetailAssetKey.value === 'game') return isGeneratingGameHtml.value;
  return false;
});

const historyDetailMaterialId = computed(() => {
  if (historyDetailAssetKey.value === 'word') return generatedResultMaterials.value.word;
  if (historyDetailAssetKey.value === 'ppt') return generatedResultMaterials.value.ppt;
  if (historyDetailAssetKey.value === 'game') return generatedResultMaterials.value.game || currentGameHtmlMaterialId.value;
  return null;
});

const historyGameMaterialUrl = computed(() =>
  previewTab.value === 'game' ? buildMaterialDownloadUrl(historyDetailMaterialId.value) : ''
);

const historyDetailCanDownload = computed(() =>
  historyDetailAssetKey.value === 'markdown'
    ? !!lessonPlanContent.value
    : !!historyDetailMaterialId.value
);

const historyDetailExportLabel = computed(() => {
  if (!historyDetailAssetKey.value) return '';
  if (historyDetailAssetKey.value === 'markdown') return '下载 Markdown';
  if (historyDetailExporting.value) return '生成中...';
  if (historyDetailAssetKey.value === 'word') return generatedResultMaterials.value.word ? '重新生成 Word' : '生成 Word';
  if (historyDetailAssetKey.value === 'ppt') return generatedResultMaterials.value.ppt ? '重新生成 PPTX' : '生成 PPTX';
  return (generatedResultMaterials.value.game || currentGameHtmlMaterialId.value) ? '重新生成小游戏' : '生成小游戏';
});

function getDefaultResultAsset(): ResultAssetKey {
  if (generatedResultMaterials.value.ppt) return 'ppt';
  if (generatedResultMaterials.value.word) return 'word';
  if (generatedResultMaterials.value.game) return 'game';
  if (deliverables.value.includes('ppt')) return 'ppt';
  if (deliverables.value.includes('word')) return 'word';
  if (deliverables.value.includes('game')) return 'game';
  return 'markdown';
}

function clearProgressTimer() {
  if (progressTimer !== null) {
    window.clearInterval(progressTimer);
    progressTimer = null;
  }
}

function clearProgressResetTimer() {
  if (progressResetTimer !== null) {
    window.clearTimeout(progressResetTimer);
    progressResetTimer = null;
  }
}

function interpolateProgressByMilestones(taskKey: ProgressTaskKey, elapsedMs: number) {
  const duration = progressTaskDurations[taskKey];
  const milestones = progressTaskMilestones[taskKey];
  const ratio = duration > 0 ? elapsedMs / duration : 0;

  if (milestones.length === 0) return 0;
  if (ratio <= milestones[0].ratio) return milestones[0].percent;

  for (let index = 1; index < milestones.length; index += 1) {
    const previous = milestones[index - 1];
    const current = milestones[index];
    if (ratio <= current.ratio) {
      const segmentRatio = (ratio - previous.ratio) / Math.max(current.ratio - previous.ratio, 0.0001);
      return previous.percent + (current.percent - previous.percent) * segmentRatio;
    }
  }

  return milestones[milestones.length - 1].percent;
}

function beginProgressTicker(forceReset = false) {
  clearProgressResetTimer();
  const nextTaskKey = activeProgressTask.value?.key ?? 'lesson';
  if (
    forceReset ||
    progressPercent.value <= 0 ||
    progressPercent.value >= 100 ||
    progressTaskKey !== nextTaskKey
  ) {
    progressTaskStartedAt = Date.now();
    progressTaskKey = nextTaskKey;
    progressPercent.value = interpolateProgressByMilestones(nextTaskKey, 0);
  } else if (!progressTaskStartedAt) {
    progressTaskStartedAt = Date.now();
    progressTaskKey = nextTaskKey;
  }
  clearProgressTimer();
  progressTimer = window.setInterval(() => {
    if (!progressTaskKey || !progressTaskStartedAt) return;
    const elapsedMs = Date.now() - progressTaskStartedAt;
    const nextPercent = interpolateProgressByMilestones(progressTaskKey, elapsedMs);
    if (nextPercent > progressPercent.value) {
      progressPercent.value = Math.min(98, nextPercent);
    }
  }, 800);
}

function completeProgressTicker() {
  clearProgressTimer();
  clearProgressResetTimer();
  progressPercent.value = 100;
  progressResetTimer = window.setTimeout(() => {
    progressPercent.value = 0;
    progressTaskStartedAt = 0;
    progressTaskKey = null;
    progressResetTimer = null;
  }, 520);
}

const availablePreviewTabs = computed<Array<{ key: PreviewTab; label: string }>>(() => {
  const tabs: Array<{ key: PreviewTab; label: string }> = [{ key: 'summary', label: '需求摘要' }];
  if (showPptControl.value) tabs.push({ key: 'ppt', label: 'PPTX 课件' });
  if (showWordControl.value) tabs.push({ key: 'docx', label: 'Word 课件' });
  if (showGameControl.value) tabs.push({ key: 'game', label: '互动小游戏' });
  tabs.push({ key: 'markdown', label: 'Markdown' });
  return tabs;
});

const historyPreviewTitle = computed(() => {
  const titleMap: Record<PreviewTab, string> = {
    summary: '需求摘要',
    ppt: 'PPTX 课件',
    docx: 'Word 课件',
    game: '互动小游戏',
    markdown: 'Markdown'
  };
  return titleMap[previewTab.value] || '历史预览';
});

const historyPreviewDescription = computed(() => {
  if (!lessonPlanSpec.value && !lessonPlanContent.value) {
    return '从左侧选择一条备课历史后，这里会展示对应版本的预览内容。';
  }
  if (previewTab.value === 'summary') {
    return '当前显示历史版本的需求摘要与教学要求，便于快速判断是否需要回退或继续修订。';
  }
  if (previewTab.value === 'ppt') {
    return generatedResultMaterials.value.ppt
      ? '当前显示该历史版本已经生成的 PPTX 文件预览，和新建备课结果页保持一致。'
      : '当前历史版本还没有关联的 PPTX 文件，生成后这里会直接显示文件预览。';
  }
  if (previewTab.value === 'docx') {
    return generatedResultMaterials.value.word
      ? '当前显示该历史版本已经生成的 Word 文件预览，和新建备课结果页保持一致。'
      : '当前历史版本还没有关联的 Word 文件，生成后这里会直接显示文件预览。';
  }
  if (previewTab.value === 'game') {
    return historyDetailMaterialId.value
      ? '当前显示该历史版本关联的互动小游戏访问链接。'
      : '当前历史版本还没有关联的互动小游戏文件，生成后这里会显示访问链接。';
  }
  return '当前显示该历史版本的 Markdown 结构化内容，可直接浏览完整文本。';
});

const historyPreviewEmptyHint = computed(() => {
  if (previewTab.value === 'ppt') return '当前历史版本还没有生成 PPTX 文件。';
  if (previewTab.value === 'docx') return '当前历史版本还没有生成 Word 文件。';
  if (previewTab.value === 'game') return '当前历史版本还没有生成互动小游戏文件。';
  return '当前没有可预览内容。';
});

const currentStepSummaryTitle = computed(() => {
  if (wizardStep.value === 1) return '当前课程选择';
  if (wizardStep.value === 2) return '当前资源选择';
  return '当前核心需求';
});

watch(activeProgressTaskKey, (next, previous) => {
  if (next) {
    beginProgressTicker(next !== previous);
    return;
  }
  if (previous) {
    completeProgressTicker();
  }
});

watch(availablePreviewTabs, (tabs) => {
  if (!tabs.some(tab => tab.key === previewTab.value)) {
    previewTab.value = tabs[0].key;
  }
}, { immediate: true });

watch(
  [resultAssetOptions, deliverables],
  () => {
    if (!resultAssetOptions.value.some(option => option.key === activeResultAsset.value)) {
      activeResultAsset.value = getDefaultResultAsset();
    }
  },
  { immediate: true, deep: true }
);

watch(
  () => formData.value.courseId,
  async (newCourseId, oldCourseId) => {
    if (newCourseId) {
      await fetchChapters(Number(newCourseId));
    } else {
      chapters.value = [];
      formData.value.chapterId = '';
    }
    if (oldCourseId && oldCourseId !== newCourseId) {
      formData.value.chapterId = '';
    }
  }
);

watch([gradeDraft, requirementDraft], () => {
  syncDraftToFormData();
  updateMissingStates();
}, { deep: true, immediate: true });

watch(deliverables, () => {
  const changed = enforceDeliverableRules();
  if (!changed) {
    persistDraftState();
  }
}, { deep: true });

watch(
  () => [readyUploadedFiles.value.length, selectedKnowledgeItems.value.length, currentSourceProcessingHash.value],
  ([uploadedCount, selectedCount, currentHash], [prevUploadedCount, prevSelectedCount, prevHash]) => {
    const uploadedCountNumber = Number(uploadedCount || 0);
    const selectedCountNumber = Number(selectedCount || 0);
    const previousSelectedCountNumber = Number(prevSelectedCount || 0);

    formData.value.useKnowledgeBase = uploadedCountNumber > 0 || selectedCountNumber > 0;
    const hadProcessed = processedSources.value.length > 0 || !!processedSourcesHash.value;
    if (prevHash !== undefined && currentHash !== prevHash && hadProcessed) {
      processedSources.value = [];
      processedSourcesHash.value = '';
      processedSourcesDirty.value = true;
    } else if (
      prevUploadedCount !== undefined &&
      uploadedCountNumber === 0 &&
      selectedCountNumber === 0 &&
      previousSelectedCountNumber === 0
    ) {
      processedSourcesDirty.value = false;
    }
  }
);

watch(
  () => [wizardStep.value, uploadedFiles.value.length, selectedKnowledgeItems.value.length],
  ([step, uploadedCount, selectedCount]) => {
    if (step !== 2) return;
    if (Number(uploadedCount || 0) + Number(selectedCount || 0) === 0) {
      resourceStepAttempted.value = false;
      return;
    }
    resourceStepAttempted.value = true;
  },
  { immediate: true }
);

watch(
  [entryMode, wizardStep, gradeDraft, deliverables, selectedKnowledgeItems, uploadedFiles, requirementDraft, chatTranscript],
  () => persistDraftState(),
  { deep: true }
);

watch(
  [entryMode, lessonPlanContent, lessonPlanSpec, sources, lessonPlanVersions, selectedVersionIndex, previewTab, deliverables, currentConversationId, activeResultAsset, generatedResultMaterials, latestGameHtmlExport],
  () => persistResultState(),
  { deep: true }
);

watch(chatTranscript, () => {
  scrollToBottom();
}, { deep: true });

function scrollToBottom() {
  setTimeout(() => {
    if (chatThreadContainer.value) {
      chatThreadContainer.value.scrollTop = chatThreadContainer.value.scrollHeight;
    }
  }, 100);
}

onMounted(async () => {
  try {
    await fetchCourses();
    await fetchKnowledgeItems();
    if (chatTranscript.value.length === 0) {
      ensureChatLead();
    }
    await fetchHistoryRecords();
  } catch (error) {
    console.error('初始化智能备课失败:', error);
    ensureChatLead();
    entryMode.value = 'launcher';
    wizardStep.value = 1;
  }
});

onBeforeUnmount(() => {
  clearProgressTimer();
  clearProgressResetTimer();
  uploadControllers.forEach(controller => controller.abort());
  uploadControllers.clear();
});

let hasInitializedPlannerNavigationScroll = false;

watch(
  () => [entryMode.value, wizardStep.value] as const,
  ([nextMode, nextStep], [prevMode, prevStep]) => {
    if (!hasInitializedPlannerNavigationScroll) {
      hasInitializedPlannerNavigationScroll = true;
      return;
    }

    const isStepChanged = nextMode === 'create' && (prevMode !== nextMode || prevStep !== nextStep);
    const isResultViewEntered = (nextMode === 'result' || nextMode === 'history') && prevMode !== nextMode;

    if (!isStepChanged && !isResultViewEntered) return;
    void scrollPlannerToTop();
  }
);

function ensureChatLead() {
  if (chatTranscript.value.length === 0) {
    chatTranscript.value.push({
      role: 'assistant',
      content: defaultAssistantPrompt,
      timestamp: Date.now(),
      quickPrompts: ideaHints.slice(0, 4)
    });
  }
}

function createDefaultGradeDraft(): GradeDraft {
  return { ...defaultGradeDraft };
}

function normalizeGradeDraft(raw?: Partial<GradeDraft> | null): GradeDraft {
  return {
    stage: String(raw?.stage || '').trim() || defaultGradeDraft.stage,
    grade: String(raw?.grade || '').trim() || defaultGradeDraft.grade,
    subject: String(raw?.subject || '').trim() || defaultGradeDraft.subject
  };
}

function createEmptyFormData(): FormDataState {
  return {
    courseId: '',
    outlineType: 'class',
    chapterId: '',
    gradeSubject: [defaultGradeDraft.stage, defaultGradeDraft.grade, defaultGradeDraft.subject].join('/'),
    duration: '',
    learningObjectives: '',
    keyPoints: '',
    studentLevel: '中等水平',
    customStudentLevel: '',
    activities: [],
    teachingStyle: '',
    assessmentMethods: [],
    detailLevel: 2,
    freeTeachingIdea: '',
    useKnowledgeBase: false
  };
}

function createEmptyRequirementDraft(): RequirementDraft {
  return {
    duration: '',
    objectives: '',
    keyPoints: '',
    difficultPoints: '',
    teachingStyle: '',
    studentPreset: '中等水平',
    customStudentPreset: '',
    detailLevel: 2,
    activities: [],
    freeTeachingIdea: ''
  };
}

function normalizeUploadedFileList(value: any): UploadedFile[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item: any): UploadedFile => {
      const status: UploadedFile['status'] = item?.status === 'failed'
        ? 'failed'
        : item?.status === 'uploading'
          ? 'uploading'
          : 'ready';

      return {
        clientId: String(item?.clientId || item?.path || `upload_${Math.random().toString(36).slice(2, 10)}`).trim(),
        name: String(item?.name || '').trim(),
        path: String(item?.path || '').trim(),
        hash: String(item?.hash || '').trim(),
        size: Number.isFinite(Number(item?.size)) ? Number(item.size) : 0,
        usage: String(item?.usage || '').trim(),
        knowledgePoint: String(item?.knowledgePoint || item?.knowledge_point || '').trim(),
        isRequired: typeof item?.isRequired === 'boolean'
          ? item.isRequired
          : typeof item?.is_required === 'boolean'
            ? item.is_required
            : null,
        status,
        progress: Number.isFinite(Number(item?.progress)) ? Number(item.progress) : 100,
        errorMessage: item?.errorMessage ? String(item.errorMessage).trim() : undefined
      };
    })
    .filter((item: UploadedFile) => Boolean(item.path));
}

function normalizeKnowledgeSelectionList(value: any): KnowledgeBaseStatusItem[] {
  if (!Array.isArray(value)) return [];
  return value
    .map((item: any) => ({
      id: Number(item?.id || 0),
      course_id: item?.course_id === null || item?.course_id === undefined || item?.course_id === ''
        ? null
        : Number(item.course_id),
      file_path: String(item?.file_path || '').trim(),
      purpose: item?.purpose ? String(item.purpose).trim() : undefined,
      status: ['pending', 'processing', 'completed', 'failed'].includes(String(item?.status || ''))
        ? String(item.status) as KnowledgeBaseStatusItem['status']
        : 'completed',
      usage: String(item?.usage || '').trim(),
      knowledgePoint: String(item?.knowledgePoint || item?.knowledge_point || '').trim(),
      isRequired: typeof item?.isRequired === 'boolean'
        ? item.isRequired
        : typeof item?.is_required === 'boolean'
          ? item.is_required
          : null,
      progress: Number.isFinite(Number(item?.progress)) ? Number(item.progress) : undefined,
      progress_detail: item?.progress_detail && typeof item.progress_detail === 'object'
        ? {
            stage: String(item.progress_detail.stage || '').trim(),
            message: item.progress_detail.message ? String(item.progress_detail.message).trim() : undefined
          }
        : undefined,
      error_message: item?.error_message ? String(item.error_message).trim() : undefined,
      created_at: item?.created_at || ''
    }))
    .filter((item: KnowledgeBaseStatusItem) => item.id > 0 && !!item.file_path);
}

function areDeliverablesEqual(left: Deliverable[], right: Deliverable[]) {
  return left.length === right.length && left.every((item, index) => item === right[index]);
}

function enforceDeliverableRules() {
  const next = Array.from(new Set(deliverables.value));
  if (next.includes('game') && !next.includes('ppt')) {
    next.push('ppt');
  }
  if (!areDeliverablesEqual(next, deliverables.value)) {
    deliverables.value = next;
    return true;
  }
  return false;
}

function isDeliverableLocked(value: Deliverable) {
  return value === 'ppt' && deliverables.value.includes('game');
}

function toggleDeliverable(value: Deliverable) {
  if (value === 'ppt' && isDeliverableLocked(value)) return;
  if (deliverables.value.includes(value)) {
    deliverables.value = deliverables.value.filter(item => item !== value);
  } else {
    deliverables.value = [...deliverables.value, value];
  }
  enforceDeliverableRules();
}

function toggleActivity(activity: string) {
  if (requirementDraft.value.activities.includes(activity)) {
    requirementDraft.value.activities = requirementDraft.value.activities.filter(item => item !== activity);
  } else {
    requirementDraft.value.activities = [...requirementDraft.value.activities, activity];
  }
}

function handleStepChipClick(index: number) {
  if (index === 0) {
    goToLauncher();
    return;
  }
  if (entryMode.value === 'create' && index >= 1 && index <= 3) {
    if (index === 2 && !canMoveFromStepOne.value) return;
    wizardStep.value = index as WizardStep;
    return;
  }
  if (index === 4 && (entryMode.value === 'result' || entryMode.value === 'history')) {
    previewTab.value = 'summary';
  }
}

function goToLauncher() {
  entryMode.value = 'launcher';
  showHistoryPanel.value = false;
}

function resetCreateState() {
  wizardStep.value = 1;
  showSummaryPanel.value = true;
  deliverables.value = ['word', 'ppt'];
  knowledgePickerOpen.value = false;
  knowledgeSearchQuery.value = '';
  selectedHistoryId.value = '';
  currentConversationId.value = '';
  gradeDraft.value = createDefaultGradeDraft();
  selectedKnowledgeItems.value = [];
  uploadedFiles.value = [];
  processedSources.value = [];
  processedSourcesHash.value = '';
  processedSourcesDirty.value = false;
  lessonPlanContent.value = '';
  lessonPlanSpec.value = null;
  sources.value = [];
  lessonPlanVersions.value = [];
  selectedVersionIndex.value = null;
  revisionRequest.value = '';
  latestGameHtmlExport.value = null;
  generatedResultMaterials.value = { word: null, ppt: null, game: null };
  activeResultAsset.value = 'markdown';
  previewTab.value = 'summary';
  selectedPptTheme.value = 'auto';
  requirementDraft.value = createEmptyRequirementDraft();
  chatDraft.value = '';
  chatTranscript.value = [];
  missingFields.value = [];
  followupPrompts.value = [];
  requirementSummary.value = null;
  structuredRequirement.value = null;
  formData.value = createEmptyFormData();
  ensureChatLead();
  clearLessonPlannerStorage();
}

function startCreateFlow() {
  resetCreateState();
  entryMode.value = 'create';
}

async function openHistoryView() {
  entryMode.value = 'history';
  wizardStep.value = 4;
  showHistoryPanel.value = false;
  selectedHistoryId.value = '';
  await fetchHistoryRecords();
}

function syncDraftToFormData() {
  formData.value.gradeSubject = [gradeDraft.value.stage, gradeDraft.value.grade, gradeDraft.value.subject].filter(Boolean).join('/');
  formData.value.duration = requirementDraft.value.duration.trim();
  formData.value.learningObjectives = requirementDraft.value.objectives.trim();
  formData.value.keyPoints = requirementDraft.value.keyPoints.trim();
  formData.value.teachingStyle = requirementDraft.value.teachingStyle.trim();
  formData.value.detailLevel = requirementDraft.value.detailLevel;
  formData.value.activities = [...requirementDraft.value.activities];
  formData.value.freeTeachingIdea = requirementDraft.value.freeTeachingIdea.trim();
  formData.value.studentLevel = requirementDraft.value.studentPreset === '自定义' ? '' : requirementDraft.value.studentPreset;
  formData.value.customStudentLevel = requirementDraft.value.studentPreset === '自定义'
    ? requirementDraft.value.customStudentPreset.trim()
    : '';
  formData.value.useKnowledgeBase = readyUploadedFiles.value.length > 0 || selectedKnowledgeItems.value.length > 0;
}

function updateMissingStates() {
  const items: string[] = [];
  if (!formData.value.courseId) items.push('课程');
  if (!formData.value.chapterId) items.push('章节');
  if (!gradeDraft.value.stage.trim()) items.push('学段');
  if (!gradeDraft.value.grade.trim()) items.push('年级');
  if (!gradeDraft.value.subject.trim()) items.push('学科');
  if (!requirementDraft.value.duration.trim()) items.push('课时长度');
  if (!requirementDraft.value.objectives.trim()) items.push('核心教学目标');
  if (!requirementDraft.value.teachingStyle.trim()) items.push('教学风格');
  if (!activeStudentLevelText.value) items.push('学生学情预设');
  missingFields.value = items;
  followupPrompts.value = buildFollowupPrompts(items);
}

function buildFollowupPrompts(items: string[]) {
  const mapping: Record<string, string> = {
    课程: '本次备课对应哪门课程？',
    章节: '本节课具体是哪个章节？',
    学段: '请补充适用学段。',
    年级: '请补充适用年级。',
    学科: '请补充学科。',
    课时长度: '这节课计划上多久？',
    核心教学目标: '这节课最想让学生掌握什么？',
    教学风格: '希望课堂更偏讲授、探究还是合作？',
    学生学情预设: '学生基础如何，需要怎样的支架？'
  };
  return items.map(item => mapping[item]).filter(Boolean);
}

function getCourseNameById(courseId: string | number) {
  return courses.value.find(course => String(course.id) === String(courseId || ''))?.name || '';
}

function getChapterTitleById(chapterId: string | number) {
  return chapters.value.find(chapter => String(chapter.id) === String(chapterId || ''))?.title || '';
}

function getFileName(filePath: string) {
  if (!filePath) return '';
  return filePath.split('/').pop() || filePath;
}

function getKnowledgePurposeLabel(purpose?: string) {
  if (purpose === 'lesson_plan') return '备课资料';
  if (purpose === 'general') return '通用资料';
  return purpose || '未分类';
}

function getKnowledgeStatusLabel(status: KnowledgeBaseStatusItem['status']) {
  switch (status) {
    case 'completed':
      return '可用';
    case 'processing':
      return '处理中';
    case 'pending':
      return '排队中';
    case 'failed':
      return '失败';
    default:
      return status;
  }
}

function isKnowledgeItemSelected(item: KnowledgeBaseStatusItem) {
  return selectedKnowledgeItems.value.some(selected => selected.id === item.id);
}

function toggleKnowledgePicker() {
  if (selectableKnowledgeItems.value.length === 0) return;
  knowledgePickerOpen.value = !knowledgePickerOpen.value;
  if (!knowledgePickerOpen.value) {
    knowledgeSearchQuery.value = '';
  }
}

function toggleKnowledgeItem(item: KnowledgeBaseStatusItem) {
  if (item.status !== 'completed') return;
  if (isKnowledgeItemSelected(item)) {
    selectedKnowledgeItems.value = selectedKnowledgeItems.value.filter(selected => selected.id !== item.id);
    return;
  }
  selectedKnowledgeItems.value = [
    ...selectedKnowledgeItems.value,
    {
      ...item,
      usage: String(item.usage || '').trim(),
      knowledgePoint: String(item.knowledgePoint || '').trim(),
      isRequired: typeof item.isRequired === 'boolean' ? item.isRequired : null
    }
  ];
}

function removeKnowledgeItem(itemId: number) {
  selectedKnowledgeItems.value = selectedKnowledgeItems.value.filter(item => item.id !== itemId);
}

async function fetchCourses() {
  try {
    const response = await courseAPI.getCourses();
    if (response && typeof response === 'object' && 'courses' in response && Array.isArray((response as any).courses)) {
      courses.value = (response as any).courses as Course[];
    }
  } catch (error) {
    console.error('获取课程列表失败:', error);
  }
}

async function fetchChapters(courseId: number) {
  try {
    const response = await courseAPI.getCourseChapters(courseId);
    if (response && typeof response === 'object' && 'status' in response && (response as any).status === 'success' && Array.isArray((response as any).chapters)) {
      chapters.value = (response as any).chapters.map((chapter: any, index: number) => ({
        id: index + 1,
        title: chapter.title
      }));
      return;
    }
    chapters.value = [];
  } catch (error) {
    console.error('获取章节失败:', error);
    chapters.value = [];
  }
}

async function fetchKnowledgeItems() {
  try {
    const response = await knowledgeBaseAPI.getKnowledgeBaseStatus();
    if (response && typeof response === 'object' && 'status' in response && (response as any).status === 'success' && Array.isArray((response as any).items)) {
      knowledgeItems.value = (response as any).items as KnowledgeBaseStatusItem[];
      return;
    }
    if (response && typeof response === 'object' && 'data' in response) {
      const data = (response as any).data;
      if (data?.status === 'success' && Array.isArray(data.items)) {
        knowledgeItems.value = data.items as KnowledgeBaseStatusItem[];
        return;
      }
    }
    knowledgeItems.value = [];
  } catch (error) {
    console.error('获取知识库状态失败:', error);
    knowledgeItems.value = [];
  }
}

function createUploadClientId() {
  return `upload_${Date.now()}_${Math.random().toString(36).slice(2, 10)}`;
}

function getFileExtension(name: string) {
  return String(name || '').split('.').pop()?.toLowerCase() || '';
}

function isVideoFile(name: string) {
  return VIDEO_FILE_EXTENSIONS.has(getFileExtension(name));
}

function formatFileSize(bytes?: number) {
  const value = Number(bytes || 0);
  if (!Number.isFinite(value) || value <= 0) return '';
  if (value < 1024) return `${value} B`;
  if (value < 1024 * 1024) return `${(value / 1024).toFixed(1)} KB`;
  if (value < 1024 * 1024 * 1024) return `${(value / (1024 * 1024)).toFixed(1)} MB`;
  return `${(value / (1024 * 1024 * 1024)).toFixed(1)} GB`;
}

function getUploadStatusLabel(file: UploadedFile) {
  if (file.status === 'uploading') {
    return file.progress > 0 ? `上传中 ${file.progress}%` : '准备上传';
  }
  if (file.status === 'failed') {
    return '上传失败';
  }
  return '已上传';
}

function getUploadErrorMessage(error: any, file: File) {
  const status = Number(error?.response?.status || 0);
  const responseMessage = String(error?.response?.data?.message || error?.response?.data?.msg || '').trim();
  const errorCode = String(error?.code || '').trim().toUpperCase();
  const fallbackMessage = String(error?.message || '').trim();
  const fileTypeText = isVideoFile(file.name) ? '视频文件' : '文件';

  if (status === 413 || file.size > MAX_TEMP_UPLOAD_SIZE_BYTES) {
    return `文件超过 200MB 上限，请压缩后再上传。`;
  }
  if (errorCode === 'ECONNABORTED' || /timeout/i.test(responseMessage) || /timeout/i.test(fallbackMessage)) {
    return `${fileTypeText}较大，上传等待超时。建议压缩视频、降低码率，或稍后在更稳定的网络下重试。`;
  }
  if (/network error/i.test(fallbackMessage) || /failed to fetch/i.test(fallbackMessage)) {
    return '网络连接中断，上传未完成，请检查网络后重试。';
  }
  if (responseMessage) {
    return responseMessage;
  }
  return '上传未完成，请稍后重试。';
}

function updateUploadedFile(clientId: string, updater: (current: UploadedFile) => UploadedFile) {
  uploadedFiles.value = uploadedFiles.value.map(file =>
    file.clientId === clientId ? updater(file) : file
  );
}

async function handleFileUpload(event: Event) {
  const target = event.target as HTMLInputElement;
  const file = target.files?.[0];
  if (!file) return;

  if (file.size > MAX_TEMP_UPLOAD_SIZE_BYTES) {
    notificationService.error('上传失败', `“${file.name}”超过 200MB 上限，请压缩后再上传。`);
    target.value = '';
    return;
  }

  const clientId = createUploadClientId();
  const controller = new AbortController();
  uploadControllers.set(clientId, controller);
  uploadedFiles.value = [
    ...uploadedFiles.value,
    {
      clientId,
      name: file.name,
      path: '',
      hash: '',
      size: file.size,
      usage: '',
      knowledgePoint: '',
      isRequired: null,
      status: 'uploading',
      progress: 0
    }
  ];

  try {
    const payload = new FormData();
    payload.append('file', file);
    const response: any = await ragAiAPI.uploadTempKnowledgeFile(payload, {
      timeout: isVideoFile(file.name) ? VIDEO_TEMP_UPLOAD_TIMEOUT_MS : DEFAULT_TEMP_UPLOAD_TIMEOUT_MS,
      signal: controller.signal,
      onUploadProgress: (progressEvent) => {
        const total = Number(progressEvent.total || file.size || 0);
        const loaded = Number(progressEvent.loaded || 0);
        const progress = total > 0 ? Math.min(99, Math.max(1, Math.round((loaded / total) * 100))) : 0;
        updateUploadedFile(clientId, current => ({
          ...current,
          progress
        }));
      }
    });
    if (response?.status !== 'success' || !response?.file_info) {
      throw new Error(response?.message || '上传失败');
    }
    updateUploadedFile(clientId, current => ({
      ...current,
      name: response.file_info.original_name,
      path: response.file_info.file_path,
      hash: response.file_info.file_hash,
      size: Number(response.file_info.file_size || file.size || 0),
      status: 'ready',
      progress: 100,
      errorMessage: undefined
    }));
    notificationService.success('上传成功', `“${file.name}”已上传，可继续补充用途和知识点。`, 3500);
    target.value = '';
  } catch (error: any) {
    console.error('上传文件失败:', error);
    const isCanceled = String(error?.code || '').toUpperCase() === 'ERR_CANCELED';
    if (isCanceled) {
      uploadedFiles.value = uploadedFiles.value.filter(item => item.clientId !== clientId);
      target.value = '';
      return;
    }
    const friendlyMessage = getUploadErrorMessage(error, file);
    updateUploadedFile(clientId, current => ({
      ...current,
      status: 'failed',
      progress: 0,
      errorMessage: friendlyMessage
    }));
    notificationService.error('上传失败', `“${file.name}”${friendlyMessage}`);
    target.value = '';
  } finally {
    uploadControllers.delete(clientId);
  }
}

function removeFile(file: UploadedFile) {
  if (file.status === 'uploading') {
    uploadControllers.get(file.clientId)?.abort();
    uploadControllers.delete(file.clientId);
  }
  uploadedFiles.value = uploadedFiles.value.filter(item => item.clientId !== file.clientId);
}

function isKnownSourceUsage(value: string) {
  const normalized = String(value || '').trim();
  if (!normalized) return false;
  return sourceUsageOptions.some(option =>
    option.value === normalized ||
    option.label === normalized
  );
}

function normalizeSourceUsageValue(value: string): SourceUsage {
  const normalized = String(value || '').trim().toLowerCase();
  if (!normalized) return 'content';
  if (normalized === 'content' || normalized.includes('内容')) return 'content';
  if (normalized === 'format' || normalized.includes('格式') || normalized.includes('排版') || normalized.includes('样式')) return 'format';
  if (normalized === 'case' || normalized.includes('案例') || normalized.includes('情境') || normalized.includes('例题')) return 'case';
  if (normalized === 'image_asset' || normalized.includes('图片') || normalized.includes('配图') || normalized.includes('素材')) return 'image_asset';
  const matched = sourceUsageOptions.find(option => option.label.toLowerCase() === normalized);
  return matched?.value || 'content';
}

function getFileTypeBadge(name: string) {
  const extension = String(name || '').split('.').pop()?.toLowerCase() || '';
  if (['doc', 'docx'].includes(extension)) return 'W';
  if (['ppt', 'pptx'].includes(extension)) return 'P';
  if (['pdf'].includes(extension)) return 'PDF';
  if (['jpg', 'jpeg', 'png', 'webp'].includes(extension)) return 'IMG';
  if (['mp4', 'mov', 'avi', 'mkv', 'webm'].includes(extension)) return 'VID';
  return 'FILE';
}

function getInvalidSourceMappedFiles() {
  return readyUploadedFiles.value
    .filter(file => !file.usage || !file.knowledgePoint.trim() || typeof file.isRequired !== 'boolean')
    .map(file => file.name);
}

function getInvalidKnowledgeMappedItems() {
  return selectedKnowledgeItems.value
    .filter(item => !item.usage || !String(item.knowledgePoint || '').trim() || typeof item.isRequired !== 'boolean')
    .map(item => getFileName(item.file_path));
}

function shouldHighlightSourceField(file: UploadedFile, field: 'usage' | 'knowledgePoint' | 'isRequired') {
  if (!resourceStepAttempted.value) return false;
  if (field === 'usage') return !String(file.usage || '').trim();
  if (field === 'knowledgePoint') return !String(file.knowledgePoint || '').trim();
  return typeof file.isRequired !== 'boolean';
}

function shouldHighlightKnowledgeField(item: KnowledgeBaseStatusItem, field: 'usage' | 'knowledgePoint' | 'isRequired') {
  if (!resourceStepAttempted.value) return false;
  if (field === 'usage') return !String(item.usage || '').trim();
  if (field === 'knowledgePoint') return !String(item.knowledgePoint || '').trim();
  return typeof item.isRequired !== 'boolean';
}

function goToRequirementStep() {
  resourceStepAttempted.value = true;
  if (!canMoveFromResourceStep.value) return;
  wizardStep.value = 3;
}

function buildSourceMappings() {
  return readyUploadedFiles.value
    .filter((file): file is UploadedFile & { isRequired: boolean } => !!file.usage && typeof file.isRequired === 'boolean')
    .map(file => ({
      filePath: file.path,
      usage: normalizeSourceUsageValue(file.usage),
      knowledgePoint: file.knowledgePoint.trim(),
      isRequired: file.isRequired
    }));
}

function buildProcessSourceMappings() {
  return readyUploadedFiles.value
    .filter((file): file is UploadedFile & { isRequired: boolean } => !!file.usage && typeof file.isRequired === 'boolean')
    .map(file => ({
      file_path: file.path,
      usage: normalizeSourceUsageValue(file.usage),
      knowledge_point: file.knowledgePoint.trim(),
      is_required: file.isRequired
    }));
}

function buildSelectedKnowledgeItemsPayload() {
  return selectedKnowledgeItems.value
    .filter((item): item is KnowledgeBaseStatusItem & { usage: string; knowledgePoint: string; isRequired: boolean } =>
      !!item.file_path &&
      !!item.usage &&
      !!String(item.knowledgePoint || '').trim() &&
      typeof item.isRequired === 'boolean'
    )
    .map(item => ({
      id: item.id,
      course_id: item.course_id,
      file_path: item.file_path,
      purpose: item.purpose,
      status: item.status,
      usage: normalizeSourceUsageValue(item.usage),
      knowledgePoint: String(item.knowledgePoint || '').trim(),
      isRequired: item.isRequired
    }));
}

async function processUploadedSources() {
  if (!canProcessSources.value) return;
  isProcessingSources.value = true;
  try {
    const response: any = await ragAiAPI.processTempSources({
      file_paths: readyUploadedFiles.value.map(file => file.path),
      source_mappings: buildProcessSourceMappings()
    });
    if (response?.status !== 'success' || !Array.isArray(response?.sources)) {
      throw new Error(response?.message || '参考资料解析失败');
    }
    processedSources.value = response.sources as ProcessedSource[];
    processedSourcesHash.value = currentSourceProcessingHash.value;
    processedSourcesDirty.value = false;
  } catch (error: any) {
    console.error('解析上传资料失败:', error);
    alert(`解析上传资料失败: ${error?.message || '未知错误'}`);
  } finally {
    isProcessingSources.value = false;
  }
}

function appendFollowupPrompt(prompt: string) {
  chatDraft.value = chatDraft.value.trim() ? `${chatDraft.value.trim()}\n${prompt}` : prompt;
}

function getChatParagraphs(content: string) {
  return String(content || '')
    .split('\n')
    .map(item => item.trim())
    .filter(Boolean);
}

function normalizeChatTurnList(value: any): ChatTurn[] {
  if (!Array.isArray(value)) return [];
  const turns: ChatTurn[] = value
    .map((item: any): ChatTurn | null => {
      const content = String(item?.content || '').trim();
      if (!content) return null;
      return {
        role: item?.role === 'user' ? 'user' : 'assistant',
        content,
        timestamp: Number.isFinite(Number(item?.timestamp)) ? Number(item.timestamp) : Date.now(),
        requirementChecklist: Array.isArray(item?.requirementChecklist)
          ? item.requirementChecklist
              .map((entry: any) => ({
                key: String(entry?.key || '').trim(),
                label: String(entry?.label || '').trim(),
                detail: String(entry?.detail || '').trim(),
                status: entry?.status === 'done' ? 'done' as const : 'pending' as const
              }))
              .filter((entry: { key: string; label: string; detail: string }) => entry.key && entry.label && entry.detail)
          : undefined,
        followupQuestion: item?.followupQuestion ? String(item.followupQuestion).trim() : undefined,
        quickPrompts: Array.isArray(item?.quickPrompts)
          ? item.quickPrompts.map((prompt: any) => String(prompt || '').trim()).filter(Boolean)
          : undefined
      };
    })
    .filter((item): item is ChatTurn => item !== null);
  return turns;
}

function buildRequirementChecklist() {
  const topicText = getChapterTitleById(formData.value.chapterId) || getCourseNameById(formData.value.courseId);
  const objectiveText = requirementDraft.value.objectives.trim();
  const knowledgeText = requirementDraft.value.keyPoints.trim() || normalizeStringList(requirementSummary.value?.knowledge_points || []).join('；');
  const durationText = requirementDraft.value.duration.trim();
  const styleText = requirementDraft.value.teachingStyle.trim();
  const activityText = requirementDraft.value.activities.join('、');
  const studentText = activeStudentLevelText.value;
  const outputText = deliverableSummaryText.value !== '未选择' ? deliverableSummaryText.value : '';

  return [
    {
      key: 'topic',
      label: '课程和章节',
      detail: topicText || '还需要确认具体课程与章节。',
      status: topicText ? 'done' as const : 'pending' as const
    },
    {
      key: 'duration',
      label: '课时长度',
      detail: durationText || '还需要确认这节课计划上多久。',
      status: durationText ? 'done' as const : 'pending' as const
    },
    {
      key: 'objectives',
      label: '教学目标',
      detail: objectiveText || '还需要确认学生这节课最终要掌握什么。',
      status: objectiveText ? 'done' as const : 'pending' as const
    },
    {
      key: 'knowledge',
      label: '核心知识点',
      detail: knowledgeText || '还需要确认这节课准备讲哪些核心知识。',
      status: knowledgeText ? 'done' as const : 'pending' as const
    },
    {
      key: 'style',
      label: '教学风格',
      detail: styleText || '还需要确认课堂更偏讲授、探究还是合作。',
      status: styleText ? 'done' as const : 'pending' as const
    },
    {
      key: 'interaction',
      label: '互动设计',
      detail: activityText || '还可以继续补充讨论、练习或互动活动设计。',
      status: activityText ? 'done' as const : 'pending' as const
    },
    {
      key: 'student',
      label: '学生基础',
      detail: studentText || '还需要确认学生基础与接受能力。',
      status: studentText ? 'done' as const : 'pending' as const
    },
    {
      key: 'output',
      label: '产出偏好',
      detail: outputText || '还可以继续确认最终希望生成哪些产出。',
      status: outputText ? 'done' as const : 'pending' as const
    }
  ];
}

function buildAssistantFollowupQuestion(items: string[]) {
  if (items.length === 0) {
    return '目前关键信息已经比较完整。如果你还想继续优化，我可以再帮你细化案例情境、互动安排或讲授顺序。';
  }
  if (items.length === 1) {
    return `我接下来想再确认一下：${buildFollowupPrompts(items)[0] || `请补充${items[0]}。`}`;
  }
  const prompts = buildFollowupPrompts(items).slice(0, 2);
  if (prompts.length > 0) {
    return `为了把需求补齐，我还想继续确认这几个点：${prompts.join('；')}`;
  }
  return `还有一些信息需要继续确认：${items.join('、')}。`;
}

async function submitTeachingIdea() {
  const message = chatDraft.value.trim();
  if (!message) return;
  ensureChatLead();
  chatTranscript.value.push({ role: 'user', content: message, timestamp: Date.now() });
  requirementDraft.value.freeTeachingIdea = requirementDraft.value.freeTeachingIdea
    ? `${requirementDraft.value.freeTeachingIdea}\n${message}`
    : message;
  chatDraft.value = '';
  await performRequirementExtraction(true);
}

async function rerunRequirementExtraction() {
  await performRequirementExtraction(true);
}

function buildFormSnapshot() {
  syncDraftToFormData();
  return {
    outlineType: 'class',
    courseId: formData.value.courseId || undefined,
    chapterId: formData.value.chapterId || undefined,
    gradeSubject: formData.value.gradeSubject,
    duration: formData.value.duration || '',
    learningObjectives: formData.value.learningObjectives || '',
    keyPoints: formData.value.keyPoints || '',
    studentLevel: activeStudentLevelText.value || '',
    teachingStyle: formData.value.teachingStyle || '',
    activities: formData.value.activities || [],
    assessmentMethods: formData.value.assessmentMethods || [],
    freeTeachingIdea: requirementDraft.value.freeTeachingIdea || ''
  };
}

function buildClarifiedRequirementPayload(): RequirementSummary {
  return {
    teaching_goals: normalizeStringList(requirementDraft.value.objectives),
    knowledge_points: normalizeStringList(requirementDraft.value.keyPoints),
    duration: requirementDraft.value.duration.trim(),
    style: requirementDraft.value.teachingStyle.trim(),
    output_targets: deliverables.value.map(value => deliveryOptions.find(item => item.value === value)?.label || value)
  };
}

function buildStructuredRequirementPayload(): StructuredRequirement {
  const base = structuredRequirement.value ? normalizeStructuredRequirementPayload(structuredRequirement.value) : createEmptyStructuredRequirement();
  return {
    ...base,
    knowledge_points: normalizeStringList(requirementDraft.value.keyPoints),
    key_points: normalizeStringList(requirementDraft.value.keyPoints),
    difficult_points: normalizeStringList(requirementDraft.value.difficultPoints),
    student_profile: {
      grade: gradeSubjectText.value,
      foundation: activeStudentLevelText.value,
      learning_preference: base.student_profile.learning_preference
    },
    style: {
      ...base.style,
      teaching_style: requirementDraft.value.teachingStyle.trim(),
      output_preference: deliverableSummaryText.value
    }
  };
}

async function performRequirementExtraction(appendAssistantResponse: boolean) {
  syncDraftToFormData();
  isSummarizingRequirement.value = true;
  try {
    const summaryResponse: any = await ragAiAPI.summarizeLessonRequirement({
      conversation_id: currentConversationId.value || undefined,
      course_id: formData.value.courseId ? Number(formData.value.courseId) : undefined,
      form_snapshot: buildFormSnapshot()
    });
    if (summaryResponse?.status === 'success' && summaryResponse?.summary) {
      requirementSummary.value = {
        teaching_goals: Array.isArray(summaryResponse.summary.teaching_goals) ? summaryResponse.summary.teaching_goals : [],
        knowledge_points: Array.isArray(summaryResponse.summary.knowledge_points) ? summaryResponse.summary.knowledge_points : [],
        duration: summaryResponse.summary.duration || '',
        style: summaryResponse.summary.style || '',
        output_targets: Array.isArray(summaryResponse.summary.output_targets) ? summaryResponse.summary.output_targets : []
      };
      applyRequirementSummaryToDraft(requirementSummary.value);
    }
  } catch (error: any) {
    console.error('生成需求摘要失败:', error);
    alert(`生成需求摘要失败: ${error?.message || '未知错误'}`);
  } finally {
    isSummarizingRequirement.value = false;
  }

  isStructuringRequirement.value = true;
  try {
    const structuredResponse: any = await ragAiAPI.structureTeachingElements({
      conversation_id: currentConversationId.value || undefined,
      course_id: formData.value.courseId ? Number(formData.value.courseId) : undefined,
      form_snapshot: buildFormSnapshot(),
      requirement_summary: requirementSummary.value || buildClarifiedRequirementPayload(),
      source_mappings: readyUploadedFiles.value.length > 0 ? buildSourceMappings() : undefined
    });
    if (structuredResponse?.status === 'success' && structuredResponse?.structured) {
      structuredRequirement.value = normalizeStructuredRequirementPayload(structuredResponse.structured);
      setLocalStorageSafely(LESSON_PLANNER_STRUCTURED_KEY, structuredRequirement.value);
      applyStructuredRequirementToDraft(structuredRequirement.value);
    }
  } catch (error: any) {
    console.error('结构化教学要素失败:', error);
    alert(`结构化教学要素失败: ${error?.message || '未知错误'}`);
  } finally {
    isStructuringRequirement.value = false;
  }

  updateMissingStates();
  if (appendAssistantResponse) {
    const assistantMessage = missingFields.value.length === 0
      ? '好的，这一轮我已经把你的核心需求整理出来了。下面这些信息我已经提取到位，你可以直接确认，也可以继续补充更细的课堂设计。'
      : '好的，我先把这轮对话里提到的要点整理出来。带勾的是我已经提取到的信息，带感叹号的是我还想继续向你确认的部分。';
    chatTranscript.value.push({
      role: 'assistant',
      content: assistantMessage,
      timestamp: Date.now(),
      requirementChecklist: buildRequirementChecklist(),
      followupQuestion: buildAssistantFollowupQuestion(missingFields.value),
      quickPrompts: followupPrompts.value.slice(0, 4)
    });
  }
}

function applyRequirementSummaryToDraft(summary: RequirementSummary) {
  if (summary.duration) requirementDraft.value.duration = summary.duration;
  if (summary.teaching_goals.length > 0) requirementDraft.value.objectives = summary.teaching_goals.join('；');
  if (summary.knowledge_points.length > 0 && !requirementDraft.value.keyPoints.trim()) {
    requirementDraft.value.keyPoints = summary.knowledge_points.join('；');
  }
  if (summary.style) requirementDraft.value.teachingStyle = summary.style;
}

function mapFoundationToPreset(foundation: string) {
  if (!foundation) return;
  if (foundation.includes('薄弱')) {
    requirementDraft.value.studentPreset = '基础薄弱';
    requirementDraft.value.customStudentPreset = '';
    return;
  }
  if (foundation.includes('中等')) {
    requirementDraft.value.studentPreset = '中等水平';
    requirementDraft.value.customStudentPreset = '';
    return;
  }
  if (foundation.includes('较高') || foundation.includes('较好')) {
    requirementDraft.value.studentPreset = '较高水平';
    requirementDraft.value.customStudentPreset = '';
    return;
  }
  requirementDraft.value.studentPreset = '自定义';
  requirementDraft.value.customStudentPreset = foundation;
}

function inferActivitiesFromStructured(structured: StructuredRequirement): string[] {
  const text = [
    ...structured.teaching_flow.map(item => `${item.title} ${item.goal}`),
    structured.style.interaction_level
  ].join(' ');
  if (!text.trim()) return [];

  const inferred: string[] = [];
  const rules: Array<{ label: string; keywords: string[] }> = [
    { label: '小组讨论', keywords: ['小组讨论', '分组讨论', '讨论'] },
    { label: '实验', keywords: ['实验', '操作'] },
    { label: '角色扮演', keywords: ['角色扮演', '情景扮演'] },
    { label: '游戏辩论', keywords: ['辩论', '游戏'] },
    { label: '演讲', keywords: ['演讲', '展示', '汇报'] },
    { label: '练习测验', keywords: ['练习', '测验', '反馈', '随堂'] }
  ];

  for (const rule of rules) {
    if (rule.keywords.some(keyword => text.includes(keyword))) {
      inferred.push(rule.label);
    }
  }
  return inferred;
}

function applyStructuredRequirementToDraft(structured: StructuredRequirement) {
  if (structured.key_points.length > 0) requirementDraft.value.keyPoints = structured.key_points.join('；');
  if (structured.difficult_points.length > 0) requirementDraft.value.difficultPoints = structured.difficult_points.join('；');
  if (structured.style.teaching_style) requirementDraft.value.teachingStyle = structured.style.teaching_style;
  if (structured.student_profile.foundation) mapFoundationToPreset(structured.student_profile.foundation);
  if (requirementDraft.value.activities.length === 0) {
    const inferredActivities = inferActivitiesFromStructured(structured);
    if (inferredActivities.length > 0) {
      requirementDraft.value.activities = inferredActivities;
    }
  }
}

function createEmptyStructuredRequirement(): StructuredRequirement {
  return {
    topic: getChapterTitleById(formData.value.chapterId) || '',
    knowledge_points: [],
    teaching_flow: [],
    key_points: [],
    difficult_points: [],
    student_profile: {
      grade: gradeSubjectText.value,
      foundation: activeStudentLevelText.value,
      learning_preference: ''
    },
    style: {
      teaching_style: requirementDraft.value.teachingStyle.trim(),
      interaction_level: '',
      output_preference: deliverableSummaryText.value
    }
  };
}

function normalizeStringList(value: any): string[] {
  if (Array.isArray(value)) return value.map(item => String(item || '').trim()).filter(Boolean);
  if (typeof value === 'string') return value.split(/[\n,，;；、]+/).map(item => item.trim()).filter(Boolean);
  return [];
}

function normalizeStructuredRequirementPayload(raw: any): StructuredRequirement {
  const flow: TeachingFlowStep[] = Array.isArray(raw?.teaching_flow)
    ? raw.teaching_flow.map((item: any, index: number) => ({
        step: Number.isFinite(Number(item?.step)) && Number(item.step) > 0 ? Math.floor(Number(item.step)) : index + 1,
        title: String(item?.title || '').trim(),
        goal: String(item?.goal || '').trim()
      })).filter((item: TeachingFlowStep) => item.title || item.goal)
    : [];
  return {
    topic: String(raw?.topic || '').trim(),
    knowledge_points: normalizeStringList(raw?.knowledge_points),
    teaching_flow: flow,
    key_points: normalizeStringList(raw?.key_points),
    difficult_points: normalizeStringList(raw?.difficult_points),
    student_profile: {
      grade: String(raw?.student_profile?.grade || '').trim(),
      foundation: String(raw?.student_profile?.foundation || '').trim(),
      learning_preference: String(raw?.student_profile?.learning_preference || '').trim()
    },
    style: {
      teaching_style: String(raw?.style?.teaching_style || '').trim(),
      interaction_level: String(raw?.style?.interaction_level || '').trim(),
      output_preference: String(raw?.style?.output_preference || '').trim()
    }
  };
}

function normalizeRevisionMeta(raw: any, fallbackVersionIndex: number, fallbackCreatedAt?: number): RevisionMeta {
  const rawVersionIndex = Number(raw?.version_index);
  const versionIndex = Number.isFinite(rawVersionIndex) && rawVersionIndex > 0 ? Math.floor(rawVersionIndex) : fallbackVersionIndex;
  const rawBasedOnIndex = Number(raw?.based_on_version_index);
  const basedOnVersionIndex = Number.isFinite(rawBasedOnIndex) && rawBasedOnIndex > 0 ? Math.floor(rawBasedOnIndex) : null;
  const rawCreatedAt = Number(raw?.created_at);
  const createdAt = Number.isFinite(rawCreatedAt) && rawCreatedAt > 0 ? Math.floor(rawCreatedAt) : (fallbackCreatedAt || Math.floor(Date.now() / 1000));
  return {
    version_index: versionIndex,
    based_on_version_index: basedOnVersionIndex,
    revision_request: String(raw?.revision_request || (versionIndex === 1 ? '初始生成' : '版本修订')).trim() || (versionIndex === 1 ? '初始生成' : '版本修订'),
    created_at: createdAt
  };
}

function normalizeSourceItemList(value: any): SourceItem[] {
  if (!Array.isArray(value)) return [];
  return value.map((item: any) => ({
    title: String(item?.title || '').trim(),
    url: String(item?.url || '').trim(),
    purpose: item?.purpose ? String(item.purpose).trim() : undefined,
    mapping: item?.mapping ? {
      usage: item.mapping.usage,
      knowledge_point: String(item.mapping.knowledge_point || '').trim(),
      is_required: Boolean(item.mapping.is_required)
    } : undefined
  })).filter((item: SourceItem) => item.title || item.url);
}

function normalizeGamePlan(raw: any, requirementSummaryPayload: any): LessonPlanSpecGamePlan {
  const topic = String(requirementSummaryPayload?.topic || requirementSummaryPayload?.chapter_title || requirementSummaryPayload?.grade_subject || '当前主题').trim() || '当前主题';
  const stages = Array.isArray(raw?.stages) && raw.stages.length > 0
    ? raw.stages.map((item: any, index: number) => ({
        id: String(item?.id || `stage_${index + 1}`).trim(),
        name: String(item?.name || `第${index + 1}关`).trim(),
        goal: String(item?.goal || '完成本关题目').trim(),
        knowledge_tags: normalizeStringList(item?.knowledge_tags).length > 0 ? normalizeStringList(item?.knowledge_tags) : [topic],
        question_count: Number.isFinite(Number(item?.question_count)) ? Number(item?.question_count) : 2,
        pass_rule: {
          min_correct: Number.isFinite(Number(item?.pass_rule?.min_correct)) ? Number(item?.pass_rule?.min_correct) : 1,
          description: String(item?.pass_rule?.description || '完成本关').trim()
        },
        review_refs: normalizeStringList(item?.review_refs),
        teacher_tip: String(item?.teacher_tip || '').trim()
      }))
    : [{
        id: 'stage_1',
        name: '基础识别',
        goal: '快速识别核心概念，建立闯关信心',
        knowledge_tags: normalizeStringList(requirementSummaryPayload?.knowledge_points).slice(0, 2),
        question_count: 3,
        pass_rule: { min_correct: 2, description: '至少答对 2 题即可通关' },
        review_refs: [],
        teacher_tip: '先用定义辨析和基础识别题热身'
      }];
  return {
    mode: String(raw?.mode || 'level_challenge').trim() || 'level_challenge',
    title: String(raw?.title || `${topic}轻量闯关`).trim(),
    objective: String(raw?.objective || `围绕“${topic}”进行互动练习`).trim(),
    theme: String(raw?.theme || 'clean').trim(),
    mechanic: String(raw?.mechanic || '闯关 + 即时反馈 + 通关总结').trim(),
    estimated_minutes: Number.isFinite(Number(raw?.estimated_minutes)) && Number(raw?.estimated_minutes) > 0 ? Number(raw.estimated_minutes) : 8,
    stages,
    score_rule: {
      base_score: Number(raw?.score_rule?.base_score || 10),
      combo_bonus: Number(raw?.score_rule?.combo_bonus || 2),
      stage_clear_bonus: Number(raw?.score_rule?.stage_clear_bonus || 5),
      time_bonus_enabled: Boolean(raw?.score_rule?.time_bonus_enabled)
    },
    feedback_style: {
      success_tone: String(raw?.feedback_style?.success_tone || '鼓励式').trim(),
      retry_tone: String(raw?.feedback_style?.retry_tone || '纠错式').trim(),
      summary_tone: String(raw?.feedback_style?.summary_tone || '诊断式').trim()
    },
    steps: normalizeStringList(raw?.steps).length > 0
      ? normalizeStringList(raw?.steps)
      : stages.map((stage: LessonPlanSpecGamePlan['stages'][number]) => `${stage.name}：${stage.goal}`),
    materials: normalizeStringList(raw?.materials),
    source_refs: normalizeStringList(raw?.source_refs)
  };
}

function normalizeLessonPlanSpecPayload(raw: any): LessonPlanSpec {
  const requirementSummaryPayload = raw?.requirement_summary || {};
  const studentProfile = requirementSummaryPayload?.student_profile || {};
  const style = requirementSummaryPayload?.style || {};
  return {
    requirement_summary: {
      topic: String(requirementSummaryPayload?.topic || '').trim(),
      grade_subject: String(requirementSummaryPayload?.grade_subject || '').trim(),
      outline_type: String(requirementSummaryPayload?.outline_type || 'class').trim() || 'class',
      chapter_title: String(requirementSummaryPayload?.chapter_title || '').trim(),
      duration: String(requirementSummaryPayload?.duration || '').trim(),
      teaching_goals: normalizeStringList(requirementSummaryPayload?.teaching_goals),
      knowledge_points: normalizeStringList(requirementSummaryPayload?.knowledge_points),
      key_points: normalizeStringList(requirementSummaryPayload?.key_points),
      difficult_points: normalizeStringList(requirementSummaryPayload?.difficult_points),
      student_profile: {
        grade: String(studentProfile?.grade || '').trim(),
        foundation: String(studentProfile?.foundation || '').trim(),
        learning_preference: String(studentProfile?.learning_preference || '').trim()
      },
      style: {
        teaching_style: String(style?.teaching_style || '').trim(),
        interaction_level: String(style?.interaction_level || '').trim(),
        output_preference: String(style?.output_preference || '').trim()
      },
      output_targets: normalizeStringList(requirementSummaryPayload?.output_targets)
    },
    source_notes: Array.isArray(raw?.source_notes) ? raw.source_notes.map((item: any) => ({
      source_kind: String(item?.source_kind || '').trim(),
      source_title: String(item?.source_title || '').trim(),
      usage: String(item?.usage || '').trim(),
      knowledge_point: String(item?.knowledge_point || '').trim(),
      required: Boolean(item?.required),
      note: String(item?.note || '').trim(),
      snippets: normalizeStringList(item?.snippets)
    })) : [],
    ppt_outline: Array.isArray(raw?.ppt_outline) ? raw.ppt_outline.map((item: any) => ({
      slide_type: String(item?.slide_type || '').trim(),
      title: String(item?.title || '').trim(),
      goal: String(item?.goal || '').trim(),
      bullets: normalizeStringList(item?.bullets),
      visual_suggestion: String(item?.visual_suggestion || '').trim(),
      source_refs: normalizeStringList(item?.source_refs)
    })) : [],
    docx_outline: Array.isArray(raw?.docx_outline) ? raw.docx_outline.map((item: any) => ({
      section_title: String(item?.section_title || '').trim(),
      section_goal: String(item?.section_goal || '').trim(),
      bullets: normalizeStringList(item?.bullets),
      source_refs: normalizeStringList(item?.source_refs)
    })) : [],
    game_plan: normalizeGamePlan(raw?.game_plan, requirementSummaryPayload)
  };
}

function buildLessonPlanVersion(payload: StoredLessonPlanSpecPayload, fallbackVersionIndex: number, fallbackCreatedAt?: number): LessonPlanVersion {
  const revisionMeta = normalizeRevisionMeta(payload.revision_meta, fallbackVersionIndex, fallbackCreatedAt);
  return {
    version_index: revisionMeta.version_index,
    lesson_plan_spec: normalizeLessonPlanSpecPayload(payload.lesson_plan_spec),
    core_spec: payload.core_spec && typeof payload.core_spec === 'object' ? payload.core_spec as Record<string, any> : null,
    sources: normalizeSourceItemList(payload.sources),
    revision_meta: revisionMeta,
    generated_assets: normalizeGeneratedAssets(payload.generated_assets),
    timestamp: revisionMeta.created_at
  };
}

function normalizeGeneratedAssets(raw: any) {
  return {
    word: Number(raw?.word) || null,
    ppt: Number(raw?.ppt) || null,
    game: Number(raw?.game) || null
  };
}

function renderLessonPlanSpecToMarkdown(spec: LessonPlanSpec) {
  const summary = spec.requirement_summary;
  const lines: string[] = [];
  const title = summary.topic || `${getOutlineTypeLabel(summary.outline_type)}备课指令集`;
  lines.push(`# ${title}`, '', '## 需求摘要');
  lines.push(`- 大纲类型：${getOutlineTypeLabel(summary.outline_type)}`);
  lines.push(`- 学段/年级/学科：${summary.grade_subject || '未填写'}`);
  if (summary.chapter_title) lines.push(`- 章节：${summary.chapter_title}`);
  lines.push(`- 时长：${summary.duration || '未填写'}`);
  lines.push(`- 教学目标：${summary.teaching_goals.join('；') || '未填写'}`);
  lines.push(`- 知识点：${summary.knowledge_points.join('；') || '未填写'}`, '', '## PPT 指令');
  spec.ppt_outline.forEach((slide, index) => {
    lines.push(`### ${index + 1}. ${slide.title || '未命名页面'}`);
    lines.push(`- 目标：${slide.goal || '无'}`);
    lines.push(`- 要点：${slide.bullets.join('；') || '无'}`, '');
  });
  lines.push('## Word 指令');
  spec.docx_outline.forEach((section, index) => {
    lines.push(`### ${index + 1}. ${section.section_title || '未命名章节'}`);
    lines.push(`- 目标：${section.section_goal || '无'}`);
    lines.push(`- 要点：${section.bullets.join('；') || '无'}`, '');
  });
  lines.push('## 小游戏方案');
  lines.push(`- 标题：${spec.game_plan.title || '无'}`);
  lines.push(`- 目标：${spec.game_plan.objective || '无'}`);
  lines.push(`- 机制：${spec.game_plan.mechanic || '无'}`);
  return lines.join('\n').trim();
}

function setLessonPlanPreviewFromVersion(version: LessonPlanVersion) {
  lessonPlanSpec.value = version.lesson_plan_spec;
  sources.value = version.sources;
  lessonPlanContent.value = renderLessonPlanSpecToMarkdown(version.lesson_plan_spec);
  selectedVersionIndex.value = version.version_index;
  previewTab.value = 'summary';
  generatedResultMaterials.value = normalizeGeneratedAssets(version.generated_assets);
  activeResultAsset.value = 'markdown';
}

async function restoreHistoryCourseContext(record: HistoryRecord | undefined, version: LessonPlanVersion | null) {
  const recordCourseId = record?.course_id;
  if (recordCourseId) {
    formData.value.courseId = String(recordCourseId);
  }

  const requirementSummary = version?.lesson_plan_spec?.requirement_summary;
  const targetChapterTitle = String(
    record?.chapter_title
    || requirementSummary?.chapter_title
    || ''
  ).trim();

  if (!formData.value.courseId) {
    formData.value.chapterId = '';
    return;
  }

  await fetchChapters(Number(formData.value.courseId));

  const explicitChapterId = String(record?.chapter_id || '').trim();
  if (explicitChapterId && chapters.value.some(chapter => String(chapter.id) === explicitChapterId)) {
    formData.value.chapterId = explicitChapterId;
    return;
  }

  if (!targetChapterTitle) {
    formData.value.chapterId = '';
    return;
  }

  const matchedChapter = chapters.value.find(chapter => String(chapter.title || '').trim() === targetChapterTitle);
  formData.value.chapterId = matchedChapter ? String(matchedChapter.id) : '';
}

function parseStoredLessonPlanSpecPayload(content: string): StoredLessonPlanSpecPayload | null {
  try {
    const parsed = JSON.parse(content);
    if (parsed?.format !== 'lesson_plan_spec_v1' || !parsed?.lesson_plan_spec) return null;
    return {
      format: parsed.format,
      lesson_plan_spec: normalizeLessonPlanSpecPayload(parsed.lesson_plan_spec),
      sources: normalizeSourceItemList(parsed.sources),
      revision_meta: parsed.revision_meta,
      core_spec: parsed.core_spec && typeof parsed.core_spec === 'object' ? parsed.core_spec : undefined,
      generated_assets: normalizeGeneratedAssets(parsed.generated_assets)
    };
  } catch {
    return null;
  }
}

function buildLessonPlanVersionsFromHistory(history: HistoryMessage[]): LessonPlanVersion[] {
  const versions: LessonPlanVersion[] = [];
  history.filter(message => message.role === 'assistant').forEach((message, index) => {
    const payload = parseStoredLessonPlanSpecPayload(message.content);
    if (!payload) return;
    versions.push(buildLessonPlanVersion(payload, index + 1, message.timestamp));
  });
  return versions.sort((a, b) => a.version_index - b.version_index);
}

function inferDeliverablesFromSpec(spec: LessonPlanSpec, fallback: Deliverable[] = ['word', 'ppt']) {
  const inferred = new Set<Deliverable>();
  const summaryText = spec.requirement_summary.output_targets.join(' ');
  if (/word|教案/i.test(summaryText) || spec.docx_outline.length > 0) inferred.add('word');
  if (/ppt/i.test(summaryText) || spec.ppt_outline.length > 0) inferred.add('ppt');
  if (/游戏|html|闯关/i.test(summaryText) || spec.game_plan.stages.length > 0) inferred.add('game');
  const next = Array.from(inferred);
  return next.length > 0 ? next : fallback;
}

function syncGeneratedAssetToVersion(assetKey: 'word' | 'ppt' | 'game', materialId: number | null) {
  const targetVersionIndex = selectedVersionIndex.value ?? lessonPlanVersions.value[lessonPlanVersions.value.length - 1]?.version_index ?? null;
  if (targetVersionIndex === null) return;
  const targetVersion = lessonPlanVersions.value.find(version => version.version_index === targetVersionIndex);
  if (!targetVersion) return;
  targetVersion.generated_assets = {
    ...normalizeGeneratedAssets(targetVersion.generated_assets),
    [assetKey]: materialId
  };
}

function clearHistorySelectionState() {
  selectedHistoryId.value = '';
  currentConversationId.value = '';
  lessonPlanContent.value = '';
  lessonPlanSpec.value = null;
  sources.value = [];
  lessonPlanVersions.value = [];
  selectedVersionIndex.value = null;
  generatedResultMaterials.value = { word: null, ppt: null, game: null };
  activeResultAsset.value = 'markdown';
  latestGameHtmlExport.value = null;
  revisionRequest.value = '';
  previewTab.value = 'summary';
  showHistoryPanel.value = false;
  localStorage.removeItem(LESSON_PLANNER_RESULT_KEY);
  localStorage.removeItem(LESSON_PLANNER_CONVERSATION_KEY);
  localStorage.removeItem(LESSON_PLANNER_GAME_EXPORT_KEY);
}

async function generateLessonPlan() {
  syncDraftToFormData();
  updateMissingStates();
  if (!canGenerate.value) return;
  if (pendingUploadedFiles.value.length > 0) {
    notificationService.warning('请等待上传完成', '仍有文件正在上传，上传完成后再开始生成。');
    return;
  }
  if (failedUploadedFiles.value.length > 0) {
    notificationService.warning('请先处理失败文件', '有文件上传失败，请删除后重新上传，或仅保留已成功上传的文件。');
    return;
  }
  if (readyUploadedFiles.value.length > 0) {
    const invalidFiles = getInvalidSourceMappedFiles();
    if (invalidFiles.length > 0) {
      notificationService.warning('请完善上传文件映射', `请先完善：${invalidFiles.join('、')}`);
      return;
    }
  }
  if (selectedKnowledgeItems.value.length > 0) {
    const invalidKnowledgeItems = getInvalidKnowledgeMappedItems();
    if (invalidKnowledgeItems.length > 0) {
      alert(`请先完善知识库文件映射：${invalidKnowledgeItems.join('、')}`);
      return;
    }
  }
  if (requirementDraft.value.freeTeachingIdea.trim() && (!requirementSummary.value || !structuredRequirement.value)) {
    await performRequirementExtraction(false);
  }
  isGenerating.value = true;
  lessonPlanSpec.value = null;
  lessonPlanContent.value = '';
  sources.value = [];
  lessonPlanVersions.value = [];
  selectedVersionIndex.value = null;
  generatedResultMaterials.value = { word: null, ppt: null, game: null };
  activeResultAsset.value = 'markdown';
  latestGameHtmlExport.value = null;
  localStorage.removeItem(LESSON_PLANNER_GAME_EXPORT_KEY);
  try {
    const requestData = {
      outlineType: 'class' as const,
      courseId: formData.value.courseId || undefined,
      chapterId: formData.value.chapterId || undefined,
      gradeSubject: formData.value.gradeSubject,
      duration: formData.value.duration || undefined,
      learningObjectives: formData.value.learningObjectives || undefined,
      keyPoints: formData.value.keyPoints || undefined,
      studentLevel: formData.value.studentLevel || undefined,
      customStudentLevel: formData.value.customStudentLevel || undefined,
      activities: formData.value.activities.length > 0 ? formData.value.activities : undefined,
      teachingStyle: formData.value.teachingStyle || undefined,
      detailLevel: formData.value.detailLevel,
      freeTeachingIdea: requirementDraft.value.freeTeachingIdea || undefined,
      useKnowledgeBase: readyUploadedFiles.value.length > 0 || selectedKnowledgeItems.value.length > 0,
      tempFiles: readyUploadedFiles.value.length > 0 ? readyUploadedFiles.value.map(file => file.path) : undefined,
      sourceMappings: readyUploadedFiles.value.length > 0 ? buildSourceMappings() : undefined,
      selectedKnowledgeItems: selectedKnowledgeItems.value.length > 0 ? buildSelectedKnowledgeItemsPayload() : undefined,
      clarifiedRequirement: buildClarifiedRequirementPayload(),
      structuredRequirement: buildStructuredRequirementPayload()
    };
    const response: LessonPlanGenerateResponse = await ragAiAPI.generateLessonPlan(requestData);
    if (response?.status !== 'success' || !response?.lesson_plan_spec) throw new Error(response?.message || '备课内容生成失败');
    const initialVersion = buildLessonPlanVersion({
      format: 'lesson_plan_spec_v1',
      lesson_plan_spec: response.lesson_plan_spec,
      sources: response.sources,
      revision_meta: response.revision_meta,
      core_spec: (response as any).core_spec,
      generated_assets: {}
    }, 1, response.revision_meta?.created_at);
    lessonPlanVersions.value = [initialVersion];
    setLessonPlanPreviewFromVersion(initialVersion);
    deliverables.value = inferDeliverablesFromSpec(initialVersion.lesson_plan_spec, deliverables.value);
    activeResultAsset.value = getDefaultResultAsset();
    entryMode.value = 'result';
    wizardStep.value = 4;
    showHistoryPanel.value = false;
    if (response.conversation_id) {
      currentConversationId.value = response.conversation_id;
      localStorage.setItem(LESSON_PLANNER_CONVERSATION_KEY, response.conversation_id);
    } else {
      currentConversationId.value = '';
      localStorage.removeItem(LESSON_PLANNER_CONVERSATION_KEY);
    }
    await fetchHistoryRecords();
  } catch (error: any) {
    console.error('生成备课内容失败:', error);
    lessonPlanContent.value = `## 生成备课内容失败\n\n${error?.message || '未知错误'}`;
    alert(`生成备课内容失败: ${error?.message || '未知错误'}`);
  } finally {
    isGenerating.value = false;
  }
}

async function fetchHistoryRecords() {
  isLoadingHistory.value = true;
  try {
    const response: any = await ragAiAPI.getConversations(formData.value.courseId ? Number(formData.value.courseId) : undefined);
    if (response?.status !== 'success' || !Array.isArray(response?.conversations)) {
      historyRecords.value = [];
      return;
    }
    historyRecords.value = response.conversations
      .filter((conversation: any) => conversation.conversation_id?.startsWith('lesson_plan_'))
      .map((record: any) => ({
        conversation_id: record.conversation_id,
        title: record.title,
        display_title: typeof record.display_title === 'string' ? record.display_title : '',
        course_id: record.course_id === null || record.course_id === undefined || record.course_id === ''
          ? null
          : Number(record.course_id),
        chapter_id: typeof record.chapter_id === 'string' ? record.chapter_id : '',
        start_time: record.start_time,
        last_time: record.last_time,
        outline_type: record.outline_type === 'course' ? 'course' : 'class',
        message_count: record.message_count,
        subject: typeof record.subject === 'string' ? record.subject : '',
        grade: typeof record.grade === 'string' ? record.grade : '',
        chapter_title: typeof record.chapter_title === 'string' ? record.chapter_title : '',
        topic: typeof record.topic === 'string' ? record.topic : ''
      }));
  } catch (error) {
    console.error('获取历史记录失败:', error);
    historyRecords.value = [];
  } finally {
    isLoadingHistory.value = false;
  }
}

async function loadHistoryRecord(conversationId: string) {
  try {
    const response: any = await ragAiAPI.getChatHistory(conversationId);
    if (response?.status !== 'success' || !Array.isArray(response?.history)) throw new Error(response?.message || '获取历史记录失败');
    const targetRecord = historyRecords.value.find(record => record.conversation_id === conversationId);
    selectedHistoryId.value = conversationId;
    currentConversationId.value = conversationId;
    entryMode.value = 'history';
    wizardStep.value = 4;
    const versions = buildLessonPlanVersionsFromHistory(response.history as HistoryMessage[]);
    if (versions.length > 0) {
      lessonPlanVersions.value = versions;
      setLessonPlanPreviewFromVersion(versions[versions.length - 1]);
      await restoreHistoryCourseContext(targetRecord, versions[versions.length - 1]);
      deliverables.value = inferDeliverablesFromSpec(versions[versions.length - 1].lesson_plan_spec, deliverables.value);
    } else {
      const assistantMessages = (response.history as HistoryMessage[]).filter(message => message.role === 'assistant');
      if (assistantMessages.length > 0) {
        lessonPlanContent.value = assistantMessages[assistantMessages.length - 1].content;
        lessonPlanSpec.value = null;
      }
      await restoreHistoryCourseContext(targetRecord, null);
    }
    localStorage.setItem(LESSON_PLANNER_CONVERSATION_KEY, conversationId);
  } catch (error: any) {
    console.error('加载历史记录失败:', error);
    alert(`加载历史记录失败: ${error?.message || '未知错误'}`);
  }
}

function openDeleteHistoryDialog(conversationId: string, title: string) {
  pendingDeleteHistory.value = { conversationId, title };
}

function closeDeleteHistoryDialog() {
  if (isDeletingHistory.value) return;
  pendingDeleteHistory.value = null;
}

async function confirmDeleteHistory() {
  if (!pendingDeleteHistory.value) return;
  const { conversationId } = pendingDeleteHistory.value;
  isDeletingHistory.value = true;
  try {
    const response: any = await ragAiAPI.deleteConversation(conversationId);
    if (response?.status !== 'success') throw new Error(response?.message || '删除备课历史失败');

    const isActiveConversation = currentConversationId.value === conversationId || selectedHistoryId.value === conversationId;
    if (isActiveConversation) {
      clearHistorySelectionState();
      entryMode.value = 'history';
      wizardStep.value = 4;
    }
    await fetchHistoryRecords();
    pendingDeleteHistory.value = null;
  } catch (error: any) {
    const message = error?.response?.data?.message || error?.message || '未知错误';
    console.error('删除备课历史失败:', error);
    alert(`删除备课历史失败: ${message}`);
  } finally {
    isDeletingHistory.value = false;
  }
}

function selectLessonPlanVersion(versionIndex: number) {
  const version = lessonPlanVersions.value.find(item => item.version_index === versionIndex);
  if (!version) return;
  setLessonPlanPreviewFromVersion(version);
}

function applyRevisionShortcut(shortcut: string) {
  revisionRequest.value = revisionRequest.value.trim() ? `${revisionRequest.value.trim()}\n${shortcut}` : shortcut;
}

async function reviseLessonPlan() {
  if (!lessonPlanSpec.value || !currentConversationId.value) {
    alert('请先加载一份可编辑的备课版本');
    return;
  }
  if (!revisionRequest.value.trim()) {
    alert('请先输入修改意见');
    return;
  }
  isRevisingLessonPlan.value = true;
  try {
    const response: ReviseLessonPlanResponse = await ragAiAPI.reviseLessonPlan({
      conversation_id: currentConversationId.value,
      lesson_plan_spec: lessonPlanSpec.value,
      revision_request: revisionRequest.value.trim()
    });
    if (response?.status !== 'success' || !response?.lesson_plan_spec) throw new Error(response?.message || '备课内容修订失败');
    const newVersion = buildLessonPlanVersion({
      format: 'lesson_plan_spec_v1',
      lesson_plan_spec: response.lesson_plan_spec,
      sources: response.sources || sources.value,
      revision_meta: response.revision_meta,
      core_spec: (response as any).core_spec,
      generated_assets: {}
    }, lessonPlanVersions.value.length + 1, response.revision_meta?.created_at);
    const existingIndex = lessonPlanVersions.value.findIndex(version => version.version_index === newVersion.version_index);
    if (existingIndex >= 0) lessonPlanVersions.value.splice(existingIndex, 1, newVersion);
    else lessonPlanVersions.value.push(newVersion);
    lessonPlanVersions.value.sort((a, b) => a.version_index - b.version_index);
    setLessonPlanPreviewFromVersion(newVersion);
    deliverables.value = inferDeliverablesFromSpec(newVersion.lesson_plan_spec, deliverables.value);
    revisionRequest.value = '';
    await fetchHistoryRecords();
  } catch (error: any) {
    console.error('修订备课内容失败:', error);
    alert(`修订备课内容失败: ${error?.message || '未知错误'}`);
  } finally {
    isRevisingLessonPlan.value = false;
  }
}

async function generateLessonPpt() {
  if (!lessonPlanSpec.value || !formData.value.courseId) return;
  const outputTargets = Array.isArray(lessonPlanSpec.value.requirement_summary?.output_targets)
    ? lessonPlanSpec.value.requirement_summary.output_targets
    : [];
  const requiresGameHtmlForPpt = deliverables.value.includes('game')
    || outputTargets.some(item => /(游戏|html|闯关)/i.test(String(item || '')));
  let resolvedGameHtmlMaterialId = currentGameHtmlMaterialId.value || generatedResultMaterials.value.game || null;
  if (requiresGameHtmlForPpt && !resolvedGameHtmlMaterialId) {
    isPreparingGameHtmlForPpt.value = true;
    try {
      resolvedGameHtmlMaterialId = await generateLessonGameHtml({ keepActiveAsset: true });
    } finally {
      isPreparingGameHtmlForPpt.value = false;
    }
    if (!resolvedGameHtmlMaterialId) {
      return;
    }
  }
  isGeneratingPpt.value = true;
  try {
    const requestData: any = {
      courseId: Number(formData.value.courseId),
      lessonPlanSpec: lessonPlanSpec.value,
      processedSources: processedSources.value,
      useGallery: true,
      conversation_id: currentConversationId.value || undefined,
      version_index: selectedVersionIndex.value ?? undefined
    };
    if (selectedPptTheme.value !== 'auto') requestData.theme = selectedPptTheme.value;
    if (requiresGameHtmlForPpt && resolvedGameHtmlMaterialId) {
      requestData.gameHtmlMaterialId = resolvedGameHtmlMaterialId;
    } else if (currentGameHtmlMaterialId.value) {
      requestData.gameHtmlMaterialId = currentGameHtmlMaterialId.value;
    }
    const response = await ragAiAPI.generateLessonPpt(requestData);
    if (response?.status !== 'success' || !response?.material_id) throw new Error(response?.message || 'PPT 生成失败');
    generatedResultMaterials.value.ppt = response.material_id;
    syncGeneratedAssetToVersion('ppt', response.material_id);
    activeResultAsset.value = 'ppt';
  } catch (error: any) {
    const message = error?.response?.data?.message || error?.message || '未知错误';
    console.error('生成PPT失败:', error);
    alert(`生成PPT失败: ${message}`);
  } finally {
    isGeneratingPpt.value = false;
  }
}

async function generateLessonDocx() {
  if (!lessonPlanSpec.value || !formData.value.courseId) return;
  isGeneratingDocx.value = true;
  try {
    const targetVersionIndex = selectedVersionIndex.value ?? lessonPlanVersions.value[lessonPlanVersions.value.length - 1]?.version_index ?? null;
    const targetVersion = lessonPlanVersions.value.find(item => item.version_index === targetVersionIndex) || null;
    const response = await ragAiAPI.generateLessonDocx({
      courseId: Number(formData.value.courseId),
      lessonPlanSpec: lessonPlanSpec.value,
      coreSpec: targetVersion?.core_spec || undefined,
      conversation_id: currentConversationId.value || undefined,
      version_index: selectedVersionIndex.value ?? undefined
    });
    if (response?.status !== 'success' || !response?.material_id) throw new Error(response?.message || 'Word 生成失败');
    generatedResultMaterials.value.word = response.material_id;
    syncGeneratedAssetToVersion('word', response.material_id);
    activeResultAsset.value = 'word';
  } catch (error: any) {
    const message = error?.response?.data?.message || error?.message || '未知错误';
    console.error('生成 Word 失败:', error);
    alert(`生成 Word 失败: ${message}`);
  } finally {
    isGeneratingDocx.value = false;
  }
}

async function generateLessonGameHtml(options: { keepActiveAsset?: boolean } = {}): Promise<number | null> {
  if (!lessonPlanSpec.value || !formData.value.courseId) return null;
  isGeneratingGameHtml.value = true;
  try {
    const requestData: any = {
      courseId: Number(formData.value.courseId),
      lessonPlanSpec: lessonPlanSpec.value,
      gamePlan: lessonPlanSpec.value.game_plan,
      conversation_id: currentConversationId.value || undefined,
      version_index: selectedVersionIndex.value ?? undefined
    };
    if (selectedPptTheme.value !== 'auto') requestData.theme = selectedPptTheme.value;
    const response = await ragAiAPI.generateLessonGameHtml(requestData);
    if (response?.status !== 'success' || !response?.material_id) throw new Error(response?.message || '小游戏 HTML 导出失败');
    latestGameHtmlExport.value = { courseId: Number(formData.value.courseId), materialId: response.material_id, title: response.material?.title || response.file_path || 'lesson-game.html' };
    generatedResultMaterials.value.game = response.material_id;
    syncGeneratedAssetToVersion('game', response.material_id);
    if (!options.keepActiveAsset) {
      activeResultAsset.value = 'game';
    }
    localStorage.setItem(LESSON_PLANNER_GAME_EXPORT_KEY, JSON.stringify(latestGameHtmlExport.value));
    return response.material_id as number;
  } catch (error: any) {
    const message = error?.response?.data?.message || error?.message || '未知错误';
    console.error('导出小游戏 HTML 失败:', error);
    alert(`导出小游戏 HTML 失败: ${message}`);
    return null;
  } finally {
    isGeneratingGameHtml.value = false;
  }
}

function formatDate(timestamp: number) {
  const date = new Date(timestamp * 1000);
  return date.toLocaleString('zh-CN', { year: 'numeric', month: '2-digit', day: '2-digit', hour: '2-digit', minute: '2-digit' });
}

function formatHistoryTimestampCompact(timestamp: number) {
  const date = new Date(timestamp * 1000);
  const year = String(date.getFullYear()).slice(-2);
  const month = String(date.getMonth() + 1).padStart(2, '0');
  const day = String(date.getDate()).padStart(2, '0');
  const hour = String(date.getHours()).padStart(2, '0');
  const minute = String(date.getMinutes()).padStart(2, '0');
  return `${year}/${month}/${day} ${hour}.${minute}`;
}

function parseGradeSubjectParts(gradeSubject: string) {
  const parts = String(gradeSubject || '')
    .split(/[\/|｜]/)
    .map(part => part.trim())
    .filter(Boolean);
  if (parts.length >= 3) {
    return { stage: parts[0], grade: parts[1], subject: parts[2] };
  }
  if (parts.length === 2) {
    return { stage: '', grade: parts[0], subject: parts[1] };
  }
  return { stage: '', grade: '', subject: parts[0] || '' };
}

function getHistoryRecordTitle(record: HistoryRecord) {
  if (record.display_title?.trim()) return record.display_title.trim();
  const lines = String(record.title || '')
    .split(/\r?\n/)
    .map(line => line.trim())
    .filter(Boolean);
  const gradeSubjectLine = lines.find(line => line.includes('学段/年级/学科'));
  const chapterLine = lines.find(line => line.includes('章节'));
  const topicLine = lines.find(line => line.includes('主题'));
  const gradeSubject = gradeSubjectLine?.split('：').slice(1).join('：').trim() || '';
  const parsed = parseGradeSubjectParts(gradeSubject);
  const chapterTitle = chapterLine?.split('：').slice(1).join('：').trim()
    || topicLine?.split('：').slice(1).join('：').trim()
    || record.chapter_title
    || record.topic
    || record.title;
  const titleParts = [
    record.subject || parsed.subject,
    record.grade || parsed.grade,
    chapterTitle,
    formatHistoryTimestampCompact(record.last_time)
  ].filter(part => String(part || '').trim());
  return titleParts.join(' ');
}

function formatDateForFilename(date: Date) {
  return `${date.getFullYear()}${String(date.getMonth() + 1).padStart(2, '0')}${String(date.getDate()).padStart(2, '0')}_${String(date.getHours()).padStart(2, '0')}${String(date.getMinutes()).padStart(2, '0')}`;
}

function downloadAsMarkdown() {
  if (!lessonPlanContent.value) return;
  const filename = `备课-${gradeSubjectText.value || '未命名'}-${formatDateForFilename(new Date())}.md`;
  const element = document.createElement('a');
  const file = new Blob([lessonPlanContent.value], { type: 'text/markdown;charset=utf-8' });
  element.href = URL.createObjectURL(file);
  element.download = filename;
  document.body.appendChild(element);
  element.click();
  document.body.removeChild(element);
}

function exportActiveResultAsset() {
  if (activeResultAsset.value === 'markdown') {
    downloadAsMarkdown();
    return;
  }
  if (activeResultAsset.value === 'word') {
    void generateLessonDocx();
    return;
  }
  if (activeResultAsset.value === 'ppt') {
    void generateLessonPpt();
    return;
  }
  void generateLessonGameHtml();
}

function exportHistoryDetailAsset() {
  if (historyDetailAssetKey.value === 'markdown') {
    downloadAsMarkdown();
    return;
  }
  if (historyDetailAssetKey.value === 'word') {
    void generateLessonDocx();
    return;
  }
  if (historyDetailAssetKey.value === 'ppt') {
    void generateLessonPpt();
    return;
  }
  if (historyDetailAssetKey.value === 'game') {
    void generateLessonGameHtml();
  }
}

function downloadActiveResult() {
  if (activeResultAsset.value === 'markdown') {
    downloadAsMarkdown();
    return;
  }
  if (!activeResultMaterialId.value) return;
  materialAPI.downloadMaterial(activeResultMaterialId.value);
}

function downloadHistoryDetailAsset() {
  if (historyDetailAssetKey.value === 'markdown') {
    downloadAsMarkdown();
    return;
  }
  if (!historyDetailMaterialId.value) return;
  materialAPI.downloadMaterial(historyDetailMaterialId.value);
}

function getOutlineTypeLabel(outlineType: string) {
  return outlineType === 'course' ? '课程总纲' : '课堂教案';
}

function setLocalStorageSafely(key: string, payload: unknown) {
  try {
    localStorage.setItem(key, JSON.stringify(payload));
    return true;
  } catch (error) {
    console.error(`写入本地缓存失败: ${key}`, error);
    return false;
  }
}

function persistDraftState() {
  const payload = {
    wizardStep: wizardStep.value,
    gradeDraft: gradeDraft.value,
    deliverables: deliverables.value,
    selectedKnowledgeItems: selectedKnowledgeItems.value,
    uploadedFiles: uploadedFiles.value,
    requirementDraft: requirementDraft.value,
    chatTranscript: chatTranscript.value,
    formData: formData.value
  };
  if (!setLocalStorageSafely(LESSON_PLANNER_DRAFT_KEY, payload)) {
    setLocalStorageSafely(LESSON_PLANNER_DRAFT_KEY, {
      wizardStep: wizardStep.value,
      gradeDraft: gradeDraft.value,
      deliverables: deliverables.value,
      selectedKnowledgeItems: selectedKnowledgeItems.value,
      uploadedFiles: uploadedFiles.value,
      requirementDraft: requirementDraft.value,
      formData: formData.value
    });
  }
}

function restoreDraftState() {
  const raw = localStorage.getItem(LESSON_PLANNER_DRAFT_KEY);
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw);
    if (parsed?.wizardStep) wizardStep.value = parsed.wizardStep;
    if (parsed?.gradeDraft) gradeDraft.value = normalizeGradeDraft(parsed.gradeDraft);
    if (Array.isArray(parsed?.deliverables)) deliverables.value = parsed.deliverables;
    if (Array.isArray(parsed?.selectedKnowledgeItems)) selectedKnowledgeItems.value = normalizeKnowledgeSelectionList(parsed.selectedKnowledgeItems);
    if (Array.isArray(parsed?.uploadedFiles)) uploadedFiles.value = normalizeUploadedFileList(parsed.uploadedFiles);
    if (parsed?.requirementDraft) requirementDraft.value = { ...requirementDraft.value, ...parsed.requirementDraft };
    if (Array.isArray(parsed?.chatTranscript)) chatTranscript.value = normalizeChatTurnList(parsed.chatTranscript);
    if (parsed?.formData) formData.value = { ...formData.value, ...parsed.formData };
    if (formData.value.gradeSubject && !gradeSubjectText.value) {
      const [stage = '', grade = '', subject = ''] = String(formData.value.gradeSubject).split('/');
      gradeDraft.value = normalizeGradeDraft({ stage, grade, subject });
    }
    showHistoryPanel.value = false;
  } catch (error) {
    console.error('恢复草稿失败:', error);
    localStorage.removeItem(LESSON_PLANNER_DRAFT_KEY);
  }
}

function persistResultState() {
  if (!lessonPlanContent.value && !lessonPlanSpec.value && lessonPlanVersions.value.length === 0) return;
  const activeVersion =
    selectedVersionIndex.value !== null
      ? lessonPlanVersions.value.find(version => version.version_index === selectedVersionIndex.value) || null
      : lessonPlanVersions.value[lessonPlanVersions.value.length - 1] || null;

  const payload = {
    entryMode: entryMode.value,
    lessonPlanContent: lessonPlanContent.value,
    lessonPlanSpec: lessonPlanSpec.value,
    sources: sources.value,
    currentVersion: activeVersion,
    selectedVersionIndex: activeVersion?.version_index ?? selectedVersionIndex.value,
    previewTab: previewTab.value,
    deliverables: deliverables.value,
    currentConversationId: currentConversationId.value,
    activeResultAsset: activeResultAsset.value,
    generatedResultMaterials: generatedResultMaterials.value,
    latestGameHtmlExport: latestGameHtmlExport.value
  };
  if (!setLocalStorageSafely(LESSON_PLANNER_RESULT_KEY, payload)) {
    setLocalStorageSafely(LESSON_PLANNER_RESULT_KEY, {
      entryMode: entryMode.value,
      previewTab: previewTab.value,
      deliverables: deliverables.value,
      currentConversationId: currentConversationId.value,
      activeResultAsset: activeResultAsset.value
    });
  }
}

function restoreResultState() {
  const raw = localStorage.getItem(LESSON_PLANNER_RESULT_KEY);
  if (!raw) return;
  try {
    const parsed = JSON.parse(raw);
    if (parsed?.lessonPlanSpec) lessonPlanSpec.value = normalizeLessonPlanSpecPayload(parsed.lessonPlanSpec);
    lessonPlanContent.value = String(parsed?.lessonPlanContent || '');
    sources.value = normalizeSourceItemList(parsed?.sources);
    if (Array.isArray(parsed?.lessonPlanVersions)) {
      lessonPlanVersions.value = parsed.lessonPlanVersions.map((version: any, index: number) => buildLessonPlanVersion({
        format: 'lesson_plan_spec_v1',
        lesson_plan_spec: version.lesson_plan_spec,
        sources: version.sources,
        revision_meta: version.revision_meta,
        core_spec: version.core_spec,
        generated_assets: version.generated_assets
      }, index + 1, version?.revision_meta?.created_at));
    } else if (parsed?.currentVersion?.lesson_plan_spec) {
      lessonPlanVersions.value = [
        buildLessonPlanVersion(
          {
            format: 'lesson_plan_spec_v1',
            lesson_plan_spec: parsed.currentVersion.lesson_plan_spec,
            sources: parsed.currentVersion.sources,
            revision_meta: parsed.currentVersion.revision_meta,
            core_spec: parsed.currentVersion.core_spec,
            generated_assets: parsed.currentVersion.generated_assets
          },
          parsed?.currentVersion?.version_index || 1,
          parsed?.currentVersion?.timestamp
        )
      ];
    }
    selectedVersionIndex.value = parsed?.selectedVersionIndex ?? null;
    previewTab.value = parsed?.previewTab || 'summary';
    if (Array.isArray(parsed?.deliverables)) deliverables.value = parsed.deliverables;
    if (parsed?.currentConversationId) currentConversationId.value = parsed.currentConversationId;
    if (parsed?.generatedResultMaterials) {
      generatedResultMaterials.value = {
        word: Number(parsed.generatedResultMaterials.word) || null,
        ppt: Number(parsed.generatedResultMaterials.ppt) || null,
        game: Number(parsed.generatedResultMaterials.game) || null
      };
    }
    if (parsed?.latestGameHtmlExport) latestGameHtmlExport.value = parsed.latestGameHtmlExport;
    if (parsed?.activeResultAsset && ['word', 'ppt', 'game', 'markdown'].includes(parsed.activeResultAsset)) {
      activeResultAsset.value = parsed.activeResultAsset;
    } else {
      activeResultAsset.value = getDefaultResultAsset();
    }
    if ((parsed?.entryMode === 'result' || parsed?.entryMode === 'history') && (lessonPlanContent.value || lessonPlanVersions.value.length > 0)) {
      entryMode.value = parsed.entryMode;
      wizardStep.value = 4;
    }
  } catch (error) {
    console.error('恢复结果失败:', error);
    localStorage.removeItem(LESSON_PLANNER_RESULT_KEY);
  }
}

function restoreLegacyLocalState() {
  const legacyConversationId = localStorage.getItem(LESSON_PLANNER_CONVERSATION_KEY);
  if (legacyConversationId) currentConversationId.value = legacyConversationId;
  const legacyStructured = localStorage.getItem(LESSON_PLANNER_STRUCTURED_KEY);
  if (legacyStructured) {
    try {
      structuredRequirement.value = normalizeStructuredRequirementPayload(JSON.parse(legacyStructured));
    } catch (error) {
      console.error('恢复旧结构化需求失败:', error);
    }
  }
  const gameExport = localStorage.getItem(LESSON_PLANNER_GAME_EXPORT_KEY);
  if (gameExport) {
    try {
      latestGameHtmlExport.value = JSON.parse(gameExport);
    } catch (error) {
      console.error('恢复小游戏导出缓存失败:', error);
    }
  }
}
</script>
<style scoped>
.lesson-planner-shell{width:100%;background:#fff}
.planner-frame{--ink:#173247;--muted:#6d7f8f;--line:rgba(23,50,71,.10);--soft:#eef3f7;background:#fff;border:1px solid rgba(23,50,71,.08);border-radius:28px;box-shadow:0 18px 42px rgba(23,50,71,.07);color:var(--ink);overflow:hidden;position:relative;isolation:isolate}
.planner-frame--breakout{--planner-frame-breakout:max(0px,calc(50vw - 50% - clamp(1rem,2vw,2rem)));overflow:visible}
.planner-frame--history-breakout{overflow:visible}
.planner-frame--breakout::after{content:'';position:absolute;top:-1px;right:calc(var(--planner-frame-breakout) * -1);bottom:-1px;width:var(--planner-frame-breakout);background:#fff;border:1px solid rgba(23,50,71,.08);border-left:none;border-radius:0 28px 28px 0;box-shadow:18px 18px 42px rgba(23,50,71,.04);pointer-events:none;z-index:0}
.planner-frame--breakout>*,.planner-frame--history-breakout>*{position:relative;z-index:1}
.planner-header,.stage-header,.summary-panel-head,.history-rail-head,.result-toolbar{display:flex;justify-content:space-between;gap:1rem;padding:1.35rem 1.5rem;border-bottom:1px solid rgba(20,50,73,.08)}
.planner-header{display:flex;flex-direction:column;padding:1.1rem 1.8rem .9rem;background:
radial-gradient(circle at top left,rgba(215,230,244,.55),transparent 32%),
radial-gradient(circle at top right,rgba(244,230,210,.52),transparent 34%),
linear-gradient(180deg,#fff 0%,#f8fbfd 100%)}
.planner-header--compact{padding-top:.8rem;padding-bottom:.75rem}
.planner-header--with-steps{gap:.35rem}
.planner-header-main{display:flex;justify-content:space-between;gap:1rem;align-items:flex-start}
.planner-header-main--compact{justify-content:flex-end}
.planner-compact-bar{display:flex;align-items:center;justify-content:space-between;gap:1.5rem;width:100%}
.planner-compact-bar--teleported{display:flex;align-items:center;justify-content:flex-end;gap:2rem;width:fit-content;max-width:100%;margin-left:auto;padding:0;border:none;border-radius:0;background:transparent;box-shadow:none}
.compact-action-btn{display:inline-flex;align-items:center;gap:.45rem;padding:.45rem 1rem;border-radius:99px;border:1px solid rgba(23,50,71,.1);background:#fff;color:#64748b;font-size:.84rem;font-weight:800;transition:all .2s ease;box-shadow:0 2px 8px rgba(23,50,71,.03);white-space:nowrap}
.compact-action-btn:hover{background:#f8fafc;color:#173247;border-color:rgba(23,50,71,.18);transform:translateY(-1px);box-shadow:0 4px 12px rgba(23,50,71,.06)}
.compact-action-btn svg{opacity:.8;color:#6366f1}
.history-btn{background:rgba(99,102,241,.03);border-color:rgba(99,102,241,.12)}
.history-btn:hover{background:rgba(99,102,241,.08);border-color:rgba(99,102,241,.2);color:#4f46e5}
.planner-compact-bar--teleported .flow-step{font-size:.84rem}
.planner-compact-bar--teleported .compact-action-btn{padding:.35rem .85rem;font-size:.82rem}
.planner-actions,.result-toolbar-left,.result-toolbar-right,.assistant-hints,.shortcut-row,.summary-tags,.followup-list{display:flex;flex-wrap:wrap;align-items:center;gap:.75rem}
.planner-actions--full{width:100%;justify-content:flex-end}
.planner-actions--inline{flex-shrink:0;justify-content:flex-end;gap:.5rem}
.planner-kicker,.summary-kicker,.stage-kicker,.launcher-card-kicker,.launcher-badge,.summary-badge{display:inline-flex;align-items:center;padding:.3rem .75rem;border-radius:999px;border:1px solid rgba(99,102,241,.15);background:rgba(99,102,241,.08);font-size:.7rem;font-weight:850;letter-spacing:.1em;text-transform:uppercase;color:#6366f1}
.planner-title{margin-top:.7rem;font-size:2rem;font-weight:700;line-height:1.1;color:#173247}.planner-subtitle{margin-top:.55rem;max-width:42rem;color:var(--muted)}
.planner-steprail{display:flex;gap:.8rem;overflow-x:auto;padding:.1rem 0 0;background:transparent;border:none;border-radius:0;box-shadow:none}
.planner-steprail--inline{flex:1;min-width:0;padding-top:0}
.planner-steprail--flow{display:flex;align-items:center;gap:.4rem;overflow:visible;flex-wrap:wrap}
.flow-step{display:inline-flex;align-items:center;gap:.5rem;padding:.4rem .85rem;border-radius:99px;background:transparent;border:none;color:#64748b;font-size:.88rem;font-weight:750;transition:all .2s cubic-bezier(.23,1,.32,1)}
.flow-step:hover{background:rgba(23,50,71,.05);color:#173247;transform:translateY(-1px)}
.flow-step.active{background:rgba(99,102,241,.1);color:#6366f1}
.flow-step.complete{color:#10b981}
.flow-step-index{display:inline-flex;align-items:center;justify-content:center;width:1.25rem;height:1.25rem;border-radius:50%;background:rgba(23,50,71,.08);font-size:.65rem;font-weight:850;color:inherit;transition:all .2s ease}
.flow-step.active .flow-step-index{background:#6366f1;color:#fff;box-shadow:0 2px 6px rgba(99,102,241,.3)}
.flow-step.complete .flow-step-index{background:rgba(16,185,129,.15);color:#059669}
.flow-step-label{white-space:nowrap}
.flow-step-arrow{display:inline-flex;align-items:center;justify-content:center;color:#cbd5e1;padding:0 .1rem}
.step-chip,.preview-tab,.planner-ghost-button,.planner-export-button,.upload-trigger,.choice-chip,.hint-chip,.tag,.missing-chip{border:1px solid rgba(23,50,71,.12);background:#fff}
.step-chip{position:relative;display:inline-flex;align-items:center;gap:.75rem;padding:.8rem 1.1rem;border-radius:22px;color:#5f7384;white-space:nowrap;min-width:10.25rem;transition:transform .18s ease,box-shadow .18s ease,border-color .18s ease,background .18s ease}
.step-chip:hover{transform:translateY(-1px);border-color:rgba(23,50,71,.18);box-shadow:0 8px 18px rgba(23,50,71,.08)}
.step-chip.active,.preview-tab.active,.planner-primary-button{background:linear-gradient(135deg,#163247,#2b5b79);color:#fffdf8;border-color:#163247;box-shadow:0 14px 28px rgba(22,50,71,.18)}
.step-chip.complete{background:linear-gradient(135deg,rgba(34,78,102,.12),rgba(57,108,83,.18));border-color:rgba(41,88,67,.24);color:#173247}
.step-chip-index{display:inline-flex;align-items:center;justify-content:center;width:2rem;height:2rem;border-radius:999px;background:rgba(23,50,71,.08);font-weight:800;color:#5f7384;flex-shrink:0}
.step-chip-copy{display:flex;flex-direction:column;gap:.15rem;min-width:0}
.step-chip-kicker{font-size:.68rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;opacity:.72}
.step-chip-label{font-size:1.04rem;font-weight:750;line-height:1.1}
.step-chip.active .step-chip-index{background:rgba(255,255,255,.16);color:#fffdf8}
.step-chip.active .step-chip-kicker,.step-chip.active .step-chip-label{color:#fffdf8}
.step-chip.complete .step-chip-index{background:rgba(41,88,67,.12);color:#295843}
.step-chip.complete .step-chip-kicker{color:#446b59}
.planner-compact-bar--teleported .planner-select.compact-select{min-height:2.2rem;padding-top:.45rem;padding-bottom:.45rem;font-size:.84rem;border-radius:999px}
.launcher-stage{padding:3rem 2rem 4rem;display:flex;flex-direction:column;align-items:center;gap:3rem;background:radial-gradient(circle at 50% 0%,rgba(99,102,241,.05) 0%,transparent 50%)}
.launcher-welcome{text-align:center;max-width:42rem}
.welcome-badge{display:inline-flex;padding:.4rem 1rem;background:rgba(99,102,241,.1);color:#6366f1;border-radius:99px;font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.1em;margin-bottom:1.5rem}
.welcome-title{font-size:2.5rem;font-weight:850;color:#173247;letter-spacing:-.02em;line-height:1.1;margin-bottom:1rem}
.welcome-desc{font-size:1.1rem;color:#6d8090;line-height:1.6}
.launcher-grid,.workspace-grid,.result-grid,.stage-form-grid,.resource-columns,.editable-grid,.summary-preview-grid,.grade-grid,.deliverable-grid,.choice-grid,.resource-item-grid,.summary-grid{display:grid;gap:1.5rem}
.launcher-grid{grid-template-columns:repeat(2,minmax(0,32rem));width:100%;max-width:68rem;justify-content:center}
.resource-columns{grid-template-columns:repeat(2,minmax(0,1fr))}
.workspace-grid{grid-template-columns:minmax(0,1.7fr) minmax(320px,.92fr);padding:0 2rem 2rem;align-items:start}
.result-grid{grid-template-columns:280px minmax(0,1.55fr) minmax(300px,1fr);padding:0 2rem 2rem;position:relative}
.workspace-grid--breakout,.result-grid--breakout{--planner-edge-gutter:clamp(1rem,2vw,2rem);--planner-summary-width:26.75rem;--planner-breakout-extra:max(0px,calc(50vw - 50% - var(--planner-edge-gutter)));position:relative;width:calc(100% + var(--planner-breakout-extra));max-width:none;margin-right:calc(var(--planner-breakout-extra) * -1)}
.workspace-grid--breakout{grid-template-columns:minmax(0,1fr) var(--planner-summary-width)}
.result-grid--breakout{grid-template-columns:280px minmax(0,1fr) var(--planner-summary-width)}
.result-grid--history.result-grid--breakout{--history-rail-width:19rem;--history-rail-gap:1rem;--planner-breakout-left:calc(var(--history-rail-width) + var(--history-rail-gap));grid-template-columns:minmax(0,1fr) var(--planner-summary-width);column-gap:1.25rem;overflow:visible;width:calc(100% + var(--planner-breakout-extra) + var(--planner-breakout-left));margin-left:calc(var(--planner-breakout-left) * -1);margin-right:calc(var(--planner-breakout-extra) * -1);padding-left:calc(2rem + var(--planner-breakout-left))}
.result-grid--preview.result-grid--breakout{--result-rail-width:8rem;grid-template-columns:minmax(0,1fr) var(--planner-summary-width);column-gap:1.25rem;overflow:visible}
.result-format-rail{position:absolute;left:calc((var(--result-rail-width) + 1rem) * -1);top:1rem;display:flex;flex-direction:column;gap:.75rem;align-self:start;width:var(--result-rail-width);padding-top:0}
.history-rail--docked{position:absolute;left:2rem;top:1rem;display:flex;flex-direction:column;gap:.75rem;align-self:start;width:var(--history-rail-width);padding-top:0;max-height:none;z-index:2}
.result-format-button{display:flex;flex-direction:column;align-items:flex-start;gap:.38rem;padding:1rem .92rem;border:1px solid rgba(23,50,71,.10);border-radius:20px;background:linear-gradient(180deg,#fff,#f8fbfc);box-shadow:0 10px 22px rgba(23,50,71,.05);color:#173247;text-align:left;transition:transform .18s ease,border-color .18s ease,box-shadow .18s ease,background .18s ease}
.result-format-button:hover{transform:translateY(-1px);border-color:rgba(23,50,71,.18);box-shadow:0 16px 28px rgba(23,50,71,.08)}
.result-format-button.active{background:linear-gradient(145deg,#173247,#28526e);border-color:#173247;color:#fffdf8;box-shadow:0 18px 34px rgba(23,50,71,.16)}
.result-format-button.ready:not(.active){border-color:rgba(57,108,83,.22);background:linear-gradient(180deg,#fff,#f6fbf8)}
.result-format-label{font-size:.92rem;font-weight:760;line-height:1.35}
.result-format-meta{font-size:.76rem;font-weight:700;color:#7a8d9c}
.result-format-button.active .result-format-meta{color:rgba(255,253,248,.8)}
.result-format-button--word.ready .result-format-meta{color:#87623f}
.result-format-button--ppt.ready .result-format-meta{color:#2f6789}
.result-format-button--game.ready .result-format-meta{color:#2f6c50}
.result-format-button--markdown.ready .result-format-meta{color:#6e4d2f}
.workspace-grid--breakout .stage-panel,.workspace-grid--breakout .summary-panel,.result-grid--breakout .result-main-panel,.result-grid--breakout .result-side-panel{min-width:0}
.workspace-grid--breakout .summary-panel,.result-grid--breakout .result-side-panel{width:var(--planner-summary-width)}
.launcher-card,.stage-card,.summary-card,.result-preview-card,.history-rail,.result-main-panel,.result-side-panel,.resource-card,.resource-item,.knowledge-card,.history-card,.version-card,.preview-outline-card,.preview-mini-card{border:1px solid rgba(23,50,71,.10);border-radius:24px;background:#fff;box-shadow:0 10px 24px rgba(23,50,71,.05)}
.launcher-card{position:relative;display:flex;align-items:flex-start;gap:1.5rem;padding:2.2rem;text-align:left;transition:all .3s cubic-bezier(.23,1,.32,1);box-shadow:0 10px 30px rgba(23,50,71,.04);overflow:hidden}
.launcher-card:hover{transform:translateY(-4px);border-color:rgba(99,102,241,.3);box-shadow:0 20px 40px rgba(99,102,241,.08)}
.launcher-card-icon{display:flex;align-items:center;justify-content:center;width:4rem;height:4rem;border-radius:18px;flex-shrink:0;transition:all .3s ease}
.create-card .launcher-card-icon{background:linear-gradient(135deg,#6366f1,#4f46e5);color:#fff}
.launcher-card--history .launcher-card-icon{background:rgba(23,50,71,.05);color:#173247}
.launcher-card:hover .launcher-card-icon{transform:scale(1.05) rotate(-2deg)}
.launcher-card-content{display:flex;flex-direction:column;gap:.6rem;flex:1}
.launcher-card-kicker{font-size:.7rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:#6366f1}
.launcher-card--history .launcher-card-kicker{color:#6d8090}
.launcher-card-title{font-size:1.5rem;font-weight:800;color:#173247}
.launcher-card-body{font-size:.95rem;color:#6d8090;line-height:1.6}
.launcher-card-arrow{position:absolute;right:1.5rem;bottom:1.5rem;color:rgba(23,50,71,.2);transition:all .3s ease;transform:translateX(-10px);opacity:0}
.launcher-card:hover .launcher-card-arrow{transform:translateX(0);opacity:1;color:#6366f1}
.field-group,.field-block{display:flex;flex-direction:column;gap:.55rem}.field-label{font-size:.88rem;font-weight:700;color:#708390}.field-label em{color:#b23b2e;font-style:normal}
.planner-input,.planner-select,.planner-textarea{width:100%;border:1px solid rgba(23,50,71,.14);border-radius:14px;background:#fff;padding:.78rem .92rem;color:#173247;outline:none;transition:border-color .2s ease,box-shadow .2s ease,background .2s ease}.planner-input::placeholder,.planner-textarea::placeholder{color:#8d9aa5;font-weight:500}.planner-select{appearance:none;-webkit-appearance:none;-moz-appearance:none;padding-right:2.8rem;background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 18 18' fill='none'%3E%3Cpath d='M4.5 6.75L9 11.25L13.5 6.75' stroke='%23606f7d' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");background-repeat:no-repeat;background-position:right .9rem center;background-size:.95rem}.planner-select.is-placeholder{color:#8d9aa5;font-weight:500}.planner-select:not(.is-placeholder),.planner-input,.planner-textarea{font-weight:650}.planner-input:focus,.planner-select:focus,.planner-textarea:focus{border-color:rgba(44,112,78,.34);box-shadow:0 0 0 4px rgba(60,129,93,.10);background:#fff}.planner-select:disabled{background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='18' height='18' viewBox='0 0 18 18' fill='none'%3E%3Cpath d='M4.5 6.75L9 11.25L13.5 6.75' stroke='%23aab2b9' stroke-width='1.8' stroke-linecap='round' stroke-linejoin='round'/%3E%3C/svg%3E");background-color:#f7f9fa;color:#9aa5ad}.compact-input,.compact-select,.compact-textarea{padding:.62rem .82rem;border-radius:12px}.compact-select{padding-right:2.35rem;background-position:right .78rem center}
.planner-primary-button,.planner-ghost-button,.planner-export-button,.upload-trigger{display:inline-flex;align-items:center;justify-content:center;gap:.4rem;min-height:2.7rem;padding:0 .95rem;border-radius:999px;font-weight:700}
.planner-export-button.alt{background:rgba(72,126,154,.10)}.planner-export-button.accent{background:rgba(122,96,58,.10)}.planner-ghost-button.danger{color:#b23b2e}
.stage-footer,.assistant-compose-actions,.resource-actions,.card-head-inline,.preview-outline-head,.resource-card-head,.resource-item-head,.followup-head{display:flex;align-items:center;justify-content:space-between;gap:.75rem}
.stage-footer,.assistant-stage,.editable-card,.summary-card,.preview-pane,.sources-strip,.result-main-panel,.result-side-panel{padding:1.5rem}
.result-main-panel--preview{padding:0;background:transparent;border:none;box-shadow:none}
.result-preview-shell{display:flex;flex-direction:column;min-height:100%;border:1px solid rgba(23,50,71,.09);border-radius:24px;background:#fff;box-shadow:0 14px 30px rgba(23,50,71,.06);overflow:hidden}
.result-preview-toolbar{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;padding:1.35rem 1.5rem;border-bottom:1px solid rgba(20,50,73,.08);background:linear-gradient(180deg,#fff,#f8fbfc)}
.result-preview-toolbar-copy{display:flex;flex-direction:column;gap:.45rem}
.result-preview-toolbar-copy h3{font-size:1.34rem;font-weight:780;line-height:1.1;color:#173247}
.result-preview-toolbar-copy p{max-width:34rem;color:#6d8090;line-height:1.62}
.result-preview-toolbar-actions{display:flex;flex-wrap:wrap;align-items:center;justify-content:flex-end;gap:.7rem}
.result-progress-slot{padding:0 1.5rem 1rem;background:linear-gradient(180deg,#f8fbfc,#fff)}
.result-theme-select{min-width:9rem}
.result-preview-body{display:flex;flex:1;min-height:46rem;background:#f8fbfd}
.result-main-panel--history-preview{position:relative;padding-left:9rem}
.history-preview-rail{width:var(--result-rail-width)}
.result-format-button--history{min-height:5.4rem}
.result-preview-body--history{display:flex;flex-direction:column;min-height:46rem;background:#f8fbfd}
.result-material-preview,.result-markdown-preview{flex:1;min-width:0;background:#fff}
.result-link-preview-wrapper {
  display: flex;
  align-items: center;
  justify-content: center;
  flex: 1;
  padding: 3rem 1.5rem;
  background: #fff;
}
.game-link-card {
  display: flex;
  flex-direction: column;
  align-items: center;
  padding: 3rem 2.5rem;
  background: #f8fbfd;
  border: 1px dashed rgba(23, 50, 71, 0.15);
  border-radius: 20px;
  text-align: center;
  max-width: 480px;
  width: 100%;
}
.game-link-icon {
  font-size: 4rem;
  margin-bottom: 1.5rem;
}
.game-link-title {
  font-size: 1.4rem;
  font-weight: 780;
  color: #173247;
  margin: 0 0 0.8rem 0;
}
.game-link-desc {
  color: #6d8090;
  line-height: 1.6;
  margin: 0 0 2rem 0;
  font-size: 1.05rem;
}
.game-link-actions {
  display: flex;
  gap: 1rem;
  justify-content: center;
}
.result-markdown-preview{padding:1.5rem}
.history-preview-content{display:flex;flex-direction:column;gap:1rem;flex:1;padding:1.5rem;background:#f8fbfd}
.history-library-shell{padding:0 2rem 2rem}
.history-library-card{border:1px solid rgba(23,50,71,.09);border-radius:24px;background:#fff;box-shadow:0 14px 30px rgba(23,50,71,.06);overflow:hidden}
.history-library-head{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;padding:1.5rem;border-bottom:1px solid rgba(20,50,73,.08);background:linear-gradient(180deg,#fff,#f8fbfc)}
.history-library-head h3{margin-top:.4rem;font-size:1.34rem;font-weight:780;line-height:1.1;color:#173247}
.history-library-head p{margin-top:.5rem;max-width:34rem;color:#6d8090;line-height:1.62}
.history-library-list{display:grid;grid-template-columns:1fr;gap:1rem;padding:1.5rem;align-content:start}
.history-card-shell{position:relative}
.history-card-shell--library{min-width:0}
.history-card--library{min-height:8.75rem;width:100%;justify-content:flex-start;align-items:flex-start}
.history-card-shell .history-card{width:100%}
.history-card{display:flex;flex-direction:column;align-items:flex-start;justify-content:flex-start;gap:.4rem}
.history-card-title{display:block;width:100%;padding-right:4.75rem;white-space:normal;word-break:break-word;overflow:visible;text-overflow:clip;line-height:1.7}
.history-card--library .history-card-title{font-size:1.22rem;font-weight:760}
.history-card-delete{position:absolute;top:.9rem;right:.9rem;z-index:2;display:inline-flex;align-items:center;justify-content:center;min-width:3.3rem;height:2rem;padding:0 .8rem;border:1px solid rgba(178,59,46,.18);border-radius:999px;background:rgba(255,255,255,.94);color:#9a3c32;font-size:.78rem;font-weight:700;line-height:1;box-shadow:0 10px 18px rgba(23,50,71,.08);transition:background .18s ease,border-color .18s ease,color .18s ease,transform .18s ease}
.history-card-delete:hover{background:#fff3f1;border-color:rgba(178,59,46,.28);color:#8a3429;transform:translateY(-1px)}
.history-card-delete:disabled{opacity:.52;cursor:not-allowed;transform:none;box-shadow:none}
.history-library-empty{min-height:24rem}
.history-rail--drawer{position:fixed;left:1rem;top:5.5rem;bottom:1rem;width:min(22rem,calc(100vw - 2rem));z-index:30;display:flex;flex-direction:column;transform:translateX(-108%);transition:transform .22s ease;overflow:hidden}
.history-rail--drawer.open{transform:translateX(0)}
.history-rail--drawer .history-list{padding:1rem;overflow:auto}
.history-rail--drawer .empty-mini-card{margin:1rem}
.planner-modal-backdrop{position:fixed;inset:0;z-index:80;display:flex;align-items:center;justify-content:center;padding:1.5rem;background:rgba(12,24,34,.32);backdrop-filter:blur(10px)}
.planner-modal{width:min(100%,34rem);border:1px solid rgba(23,50,71,.1);border-radius:28px;background:linear-gradient(180deg,#fff,#fbfdff);box-shadow:0 24px 60px rgba(15,33,48,.22);overflow:hidden}
.planner-modal--danger{border-color:rgba(178,59,46,.16)}
.planner-modal-head{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;padding:1.35rem 1.5rem 1rem;border-bottom:1px solid rgba(23,50,71,.08);background:linear-gradient(180deg,rgba(255,255,255,.98),rgba(250,252,254,.92))}
.planner-modal-head h3{margin-top:.45rem;font-size:1.34rem;font-weight:800;line-height:1.15;color:#173247}
.summary-kicker--danger{color:#b23b2e;border-color:rgba(178,59,46,.15);background:rgba(178,59,46,.08)}
.planner-modal-close{display:inline-flex;align-items:center;justify-content:center;min-width:3.6rem;height:2.3rem;padding:0 .9rem;border:1px solid rgba(23,50,71,.1);border-radius:999px;background:#fff;color:#617585;font-size:.82rem;font-weight:700}
.planner-modal-close:disabled{opacity:.52;cursor:not-allowed}
.planner-modal-body{display:flex;flex-direction:column;gap:1rem;padding:1.35rem 1.5rem 1.1rem}
.planner-modal-lead{color:#5f7384;line-height:1.7}
.planner-modal-record{display:flex;flex-direction:column;gap:.42rem;padding:1rem 1.05rem;border:1px solid rgba(178,59,46,.12);border-radius:20px;background:linear-gradient(180deg,rgba(255,248,246,.98),rgba(255,252,251,.96))}
.planner-modal-record-label{font-size:.76rem;font-weight:800;letter-spacing:.08em;text-transform:uppercase;color:#a35b50}
.planner-modal-record strong{font-size:1rem;line-height:1.55;color:#173247;word-break:break-word}
.planner-modal-record span:last-child{color:#7b625d;line-height:1.62}
.planner-modal-warning{display:flex;align-items:flex-start;gap:.7rem;padding:.95rem 1rem;border-radius:18px;background:rgba(23,50,71,.04)}
.planner-modal-warning-dot{flex-shrink:0;width:.72rem;height:.72rem;margin-top:.34rem;border-radius:999px;background:linear-gradient(135deg,#b23b2e,#d7845f)}
.planner-modal-warning p{color:#667987;line-height:1.66}
.planner-modal-actions{display:flex;justify-content:flex-end;gap:.8rem;padding:0 1.5rem 1.5rem}
.planner-danger-button{display:inline-flex;align-items:center;justify-content:center;min-width:6.2rem;height:2.85rem;padding:0 1.15rem;border:none;border-radius:999px;background:linear-gradient(135deg,#a3382d,#cb5a43);color:#fffdf8;font-size:.92rem;font-weight:800;box-shadow:0 14px 26px rgba(178,59,46,.22);transition:transform .18s ease,box-shadow .18s ease,opacity .18s ease}
.planner-danger-button:hover:not(:disabled){transform:translateY(-1px);box-shadow:0 18px 30px rgba(178,59,46,.28)}
.planner-danger-button:disabled{opacity:.58;cursor:not-allowed;transform:none;box-shadow:none}
.result-empty-state--action{gap:.65rem}
.result-empty-note{max-width:26rem;text-align:center;color:#6d8090;line-height:1.58}
.result-material-preview :deep(.material-preview-container){height:100%;border:none;border-radius:0;box-shadow:none;background:#fff}
.result-material-preview :deep(.preview-area){padding:0}
.result-material-preview :deep(.preview-content){padding:0}
.result-material-preview :deep(.preview-body){min-height:46rem}
.result-material-preview :deep(.office-preview .mt-4.flex.flex-col.gap-3.rounded-xl.bg-gray-50.p-4.md\:flex-row.md\:items-center.md\:justify-between){margin:1rem 1.5rem 1.5rem}
.step-one-card .stage-header{padding:2.5rem 2rem 1.5rem;border-bottom:none;background:transparent}
.stage-header-content{display:flex;flex-direction:column;gap:.5rem}
.stage-form-grid{padding:0 2rem;gap:2rem}
.field-block{padding:0 2rem;margin-top:2rem}
.input-with-label{position:relative;flex:1}
.grade-grid{grid-template-columns:repeat(3,1fr);gap:1rem}
.stage-footer{margin-top:3rem;padding:2rem;border-top:1px solid rgba(23,50,71,.05);display:flex;justify-content:space-between;align-items:center}
.field-hint{margin-top:1rem;color:#94a3b8;font-size:.85rem;font-style:italic}
.resource-columns-modern{display:flex;flex-direction:column;gap:2rem;padding:0 2rem}
.resource-card-modern{display:flex;flex-direction:column;gap:1.5rem;padding:2rem;border:1px solid rgba(23,50,71,.06);border-radius:24px;background:#fff;box-shadow:0 10px 30px rgba(23,50,71,.03);transition:all .3s ease}
.resource-card-modern:hover{border-color:rgba(99,102,241,.12);box-shadow:0 15px 40px rgba(23,50,71,.05)}
.resource-card-head{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem}
.head-info h4{font-size:1.1rem;font-weight:850;color:#173247;display:flex;align-items:center;gap:.6rem;margin-bottom:.3rem}
.head-icon{color:#6366f1;opacity:.8}
.head-info p{font-size:.85rem;color:#94a3b8}
.upload-trigger-modern{display:inline-flex;align-items:center;padding:.5rem 1rem;background:rgba(99,102,241,.06);color:#6366f1;border:1.5px dashed rgba(99,102,241,.2);border-radius:12px;font-size:.84rem;font-weight:800;cursor:pointer;transition:all .2s ease}
.upload-trigger-modern:hover{background:rgba(99,102,241,.12);border-color:#6366f1}
.upload-trigger-modern.disabled{opacity:.55;cursor:not-allowed;pointer-events:none}
.empty-resource-placeholder{display:flex;flex-direction:column;align-items:center;justify-content:center;padding:3rem 1.5rem;border:1.5px dashed rgba(23,50,71,.08);border-radius:20px;background:rgba(23,50,71,.01);color:#94a3b8;gap:.8rem}
.empty-icon{color:rgba(23,50,71,.1)}
.resource-list-modern{display:flex;flex-direction:column;gap:1rem}
.resource-item-modern{padding:1.2rem;border:1px solid rgba(23,50,71,.08);border-radius:18px;background:rgba(23,50,71,.01);transition:all .2s ease}
.resource-item-modern:hover{background:#fff;border-color:rgba(99,102,241,.15);box-shadow:0 8px 16px rgba(23,50,71,.03)}
.resource-item-modern.is-uploading{border-color:rgba(99,102,241,.22);background:rgba(99,102,241,.03)}
.resource-item-modern.is-failed{border-color:rgba(239,68,68,.18);background:rgba(239,68,68,.03)}
.item-header{display:flex;align-items:center;justify-content:space-between;margin-bottom:1rem}
.file-info{display:flex;align-items:center;gap:.8rem}
.file-type-icon{display:inline-flex;align-items:center;justify-content:center;width:2.5rem;height:2.5rem;border-radius:10px;background:#6366f1;color:#fff;font-size:.65rem;font-weight:900;text-transform:uppercase}
.file-type-icon.kb{background:#f59e0b}
.file-name{font-size:.95rem;font-weight:750;color:#173247}
.file-submeta{display:flex;align-items:center;gap:.5rem;flex-wrap:wrap;margin-top:.25rem;font-size:.76rem;color:#64748b}
.status-chip{display:inline-flex;align-items:center;padding:.16rem .55rem;border-radius:999px;font-size:.72rem;font-weight:800}
.status-chip.uploading{background:rgba(99,102,241,.1);color:#4f46e5}
.status-chip.ready{background:rgba(16,185,129,.1);color:#059669}
.status-chip.failed{background:rgba(239,68,68,.1);color:#dc2626}
.remove-btn-icon{display:flex;align-items:center;justify-content:center;width:2rem;height:2rem;border-radius:50%;border:none;background:transparent;color:#94a3b8;transition:all .2s ease}
.remove-btn-icon:hover{background:rgba(239,68,68,.1);color:#ef4444}
.upload-status-panel{margin:-.15rem 0 1rem;padding:.85rem 1rem;border-radius:14px;border:1px solid rgba(23,50,71,.08);background:#fff}
.upload-status-panel.uploading{border-color:rgba(99,102,241,.12);background:rgba(99,102,241,.03)}
.upload-status-panel.failed{border-color:rgba(239,68,68,.12);background:rgba(239,68,68,.03)}
.upload-progress-shell{height:.5rem;border-radius:999px;background:rgba(99,102,241,.12);overflow:hidden}
.upload-progress-bar{height:100%;border-radius:999px;background:linear-gradient(90deg,#6366f1,#818cf8);transition:width .25s ease}
.upload-status-copy{margin-top:.55rem;font-size:.78rem;line-height:1.5;color:#5f7384}
.item-form-grid{display:grid;grid-template-columns:repeat(3,1fr);gap:1.5rem}
.field-group-modern{display:flex;flex-direction:column;gap:.35rem}
.field-group-modern .field-label{font-size:.75rem;font-weight:800;color:#64748b;display:flex;align-items:center;gap:.3rem}
.field-icon-small{opacity:.7}
.planner-select-modern,.planner-input-modern{width:100%;height:2.4rem;padding:0 .75rem;border:1px solid rgba(23,50,71,.12);border-radius:10px;background:#fff;font-size:.85rem;font-weight:700;color:#173247;outline:none;transition:all .2s ease}
.planner-select-modern:focus,.planner-input-modern:focus{border-color:#6366f1;box-shadow:0 0 0 3px rgba(99,102,241,.08)}
.planner-select-modern.is-invalid,.planner-input-modern.is-invalid{border-color:#ef4444;background:rgba(239,68,68,.02)}
.resource-actions-modern{display:flex;align-items:center;justify-content:space-between;margin-top:.5rem;padding-top:1rem;border-top:1px solid rgba(23,50,71,.05)}
.process-btn{display:inline-flex;align-items:center;gap:.5rem;padding:.5rem 1.2rem;background:#173247;color:#fff;border:none;border-radius:12px;font-size:.88rem;font-weight:800;cursor:pointer;transition:all .2s ease}
.process-btn:hover:not(:disabled){background:#244b67;transform:translateY(-1px);box-shadow:0 4px 12px rgba(23,50,71,.15)}
.process-btn:disabled{opacity:.5;cursor:not-allowed}
.status-badge{display:inline-flex;align-items:center;gap:.4rem;padding:.35rem .85rem;border-radius:99px;font-size:.78rem;font-weight:850}
.status-badge.success{background:rgba(16,185,129,.1);color:#059669}
.status-badge.warn{background:rgba(245,158,11,.1);color:#d97706}
.count-badge{display:inline-flex;padding:.3rem .8rem;background:rgba(16,185,129,.1);color:#059669;border-radius:99px;font-size:.75rem;font-weight:850}
.knowledge-picker-modern{position:relative}
.picker-trigger{display:flex;align-items:center;justify-content:space-between;width:100%;padding:1rem 1.2rem;border:1.5px solid rgba(23,50,71,.08);border-radius:16px;background:rgba(23,50,71,.02);color:#64748b;font-weight:750;transition:all .3s ease;cursor:pointer}
.picker-trigger:hover:not(:disabled){background:#fff;border-color:rgba(99,102,241,.2);color:#173247;box-shadow:0 8px 20px rgba(23,50,71,.04)}
.picker-trigger.active{background:#fff;border-color:#6366f1;color:#173247;box-shadow:0 8px 20px rgba(99,102,241,.08)}
.trigger-left{display:flex;align-items:center;gap:.8rem}
.picker-dropdown{position:absolute;top:calc(100% + .5rem);left:0;right:0;background:#fff;border:1px solid rgba(23,50,71,.1);border-radius:18px;box-shadow:0 20px 50px rgba(23,50,71,.12);z-index:100;overflow:hidden;animation:dropdownFade .25s ease-out}
@keyframes dropdownFade{from{opacity:0;transform:translateY(-10px)}to{opacity:1;transform:translateY(0)}}
.picker-search{padding:1rem;background:rgba(23,50,71,.02);border-bottom:1px solid rgba(23,50,71,.05)}
.picker-search-input{width:100%;height:2.6rem;padding:0 1rem;border:1px solid rgba(23,50,71,.1);border-radius:12px;font-size:.9rem;font-weight:700;outline:none;transition:all .2s ease}
.picker-search-input:focus{border-color:#6366f1;background:#fff}
.picker-options{max-height:18rem;overflow-y:auto;padding:.5rem}
.picker-option{display:flex;align-items:center;justify-content:space-between;width:100%;padding:.8rem 1rem;border:none;background:transparent;border-radius:12px;text-align:left;transition:all .2s ease;cursor:pointer}
.picker-option:hover{background:rgba(99,102,241,.05)}
.picker-option.active{background:rgba(99,102,241,.1)}
.option-title{font-size:.9rem;font-weight:800;color:#173247;margin-bottom:.2rem}
.option-meta{font-size:.75rem;color:#94a3b8}
.option-check{color:#6366f1}
.stage-guide-modern{display:flex;align-items:center;margin:1.5rem 2rem 0;padding:1.2rem 1.5rem;border-radius:18px;background:rgba(99,102,241,.05);color:#4f46e5;font-size:.9rem;font-weight:750;line-height:1.5;border:1px solid rgba(99,102,241,.1)}
.stage-guide-modern.warn{background:rgba(245,158,11,.05);color:#d97706;border-color:rgba(245,158,11,.1)}
.mini-spinner{width:14px;height:14px;border:2px solid rgba(255,255,255,.3);border-top-color:#fff;border-radius:50%;animation:spin .8s linear infinite}
@keyframes spin{to{transform:rotate(360deg)}}
.assistant-stage-modern{display:flex;flex-direction:column;gap:0;padding:0;background:rgba(23,50,71,.01);border-radius:0 0 24px 24px;overflow:hidden}
.chat-thread-container{height:560px;overflow-y:auto;padding:1.6rem 1.8rem;display:flex;flex-direction:column;gap:1.1rem;background:#fff;scroll-behavior:smooth}
.assistant-thread-modern{display:flex;flex-direction:column;gap:2rem}
.chat-row-modern{display:flex;align-items:flex-start;gap:1rem;max-width:90%}
.chat-row-modern.assistant{align-self:flex-start}
.chat-row-modern.user{align-self:flex-end;flex-direction:row-reverse}
.ai-avatar-modern{flex-shrink:0;width:2.8rem;height:2.8rem}
.user-avatar-modern{flex-shrink:0;width:2.35rem;height:2.35rem;border-radius:999px;background:linear-gradient(135deg,#244b67,#1b3550);color:#fff;display:flex;align-items:center;justify-content:center;font-size:.86rem;font-weight:800;box-shadow:0 6px 16px rgba(23,50,71,.16);overflow:hidden}
.user-avatar-image-modern{width:100%;height:100%;object-fit:cover}
.ai-icon-glow{width:100%;height:100%;border-radius:50%;background:rgba(99,102,241,.1);padding:.4rem;box-shadow:0 0 15px rgba(99,102,241,.2);display:flex;align-items:center;justify-content:center}
.ai-icon-glow img{width:1.8rem;height:1.8rem;object-fit:contain}
.bubble-wrapper{display:flex;flex-direction:column;gap:.5rem;max-width:calc(100% - 4rem)}
.chat-row-modern.user .bubble-wrapper{align-items:flex-end;max-width:min(92%,42rem);width:auto}
.bubble-modern{padding:1.2rem 1.5rem;border-radius:20px;font-size:.95rem;line-height:1.6;position:relative;box-shadow:0 4px 15px rgba(23,50,71,.03)}
.bubble-modern.assistant{background:#f8fafc;color:#173247;border-top-left-radius:4px;border:1px solid rgba(23,50,71,.05)}
.bubble-modern.user{padding:.72rem 1rem;border-radius:16px;background:linear-gradient(135deg,#2d6f9f,#255d86);color:#fff;border-top-right-radius:6px;border:1px solid rgba(23,50,71,.12);box-shadow:0 6px 14px rgba(37,93,134,.2);width:max-content;max-width:min(100%,42rem)}
.chat-row-modern.user .chat-paragraphs{max-width:100%}
.chat-row-modern.user .chat-paragraphs p{margin:0;white-space:pre-wrap;word-break:break-word;overflow-wrap:break-word}
.chat-paragraphs p{margin-bottom:.8rem}.chat-paragraphs p:last-child{margin-bottom:0}
.requirement-checklist-modern{margin-top:.9rem;display:flex;flex-direction:column;gap:.5rem;padding:.7rem;background:#fff;border-radius:12px;border:1px solid rgba(23,50,71,.05)}
.check-item-modern{display:flex;gap:.55rem;padding:.55rem .65rem;border-radius:10px;transition:all .2s ease;border:1px solid transparent}
.check-item-modern.done{background:rgba(16,185,129,.04)}
.check-item-modern.pending{background:rgba(245,158,11,.04)}
.check-icon-modern{flex-shrink:0;width:1.25rem;height:1.25rem;border-radius:50%;display:flex;align-items:center;justify-content:center}
.done .check-icon-modern{background:#10b981;color:#fff}
.pending .check-icon-modern{background:rgba(245,158,11,.2);color:#d97706}
.check-label{font-size:.82rem;font-weight:800;color:#173247;line-height:1.35}
.check-detail{font-size:.76rem;color:#64748b;margin-top:.06rem;line-height:1.35}
.followup-box-modern{margin-top:1.2rem;padding:1rem;background:rgba(99,102,241,.04);border-left:3px solid #6366f1;border-radius:0 12px 12px 0}
.followup-label{font-size:.75rem;font-weight:900;color:#6366f1;display:flex;align-items:center;gap:.4rem;margin-bottom:.4rem;text-transform:uppercase;letter-spacing:.05em}
.quick-prompts-modern{margin-top:1rem;display:flex;flex-wrap:wrap;gap:.6rem}
.prompt-pill-modern{padding:.45rem 1rem;background:#fff;border:1.5px solid rgba(99,102,241,.15);color:#6366f1;border-radius:99px;font-size:.84rem;font-weight:750;cursor:pointer;transition:all .2s ease}
.prompt-pill-modern:hover{background:#6366f1;color:#fff;transform:translateY(-1px);box-shadow:0 4px 10px rgba(99,102,241,.2)}
.input-section-modern{padding:.75rem 1.5rem .9rem;background:#f9fbfd}
.compose-box-modern{position:relative}
.textarea-wrapper-modern{display:flex;align-items:center;gap:.8rem;border:1.5px solid rgba(23,50,71,.10);border-radius:16px;background:#fff;transition:all .3s ease;box-shadow:0 3px 10px rgba(23,50,71,.02);padding:.55rem .7rem .55rem 1rem}
.textarea-wrapper-modern:focus-within{border-color:#4e7aa0;box-shadow:0 0 0 3px rgba(78,122,160,.12)}
.chat-textarea-modern{flex:1;min-width:0;height:1.45rem;max-height:1.45rem;padding:0;border:0!important;outline:0!important;box-shadow:none!important;appearance:none;-webkit-appearance:none;resize:none;font-size:.92rem;font-weight:600;color:#173247;background:transparent;line-height:1.45;overflow:hidden}
.chat-textarea-modern:focus,.chat-textarea-modern:focus-visible{border:0!important;outline:0!important;box-shadow:none!important}
.compose-actions-modern{display:flex;align-items:center;justify-content:flex-end;gap:.7rem;flex-shrink:0;padding:0;background:transparent;border-top:none}
.button-group-modern{display:flex;align-items:center;gap:.65rem}
.circle-btn-modern{width:2.8rem;height:2.8rem;border-radius:50%;display:flex;align-items:center;justify-content:center;border:1px solid rgba(23,50,71,.1);background:#fff;color:#64748b;cursor:pointer;transition:all .2s ease}
.circle-btn-modern:hover:not(:disabled){border-color:#6366f1;color:#6366f1;background:rgba(99,102,241,.05)}
.voice-btn:active{transform:scale(0.95)}
.stop-btn{background:#fff1f2;border-color:#fecaca;color:#ef4444}
.pulse-red{animation:redPulse 1.5s infinite}
@keyframes redPulse{0%{box-shadow:0 0 0 0 rgba(239,68,68,0.4)}70%{box-shadow:0 0 0 10px rgba(239,68,68,0)}100%{box-shadow:0 0 0 0 rgba(239,68,68,0)}}
.send-btn-modern{display:inline-flex;align-items:center;gap:.6rem;padding:0 1.5rem;height:2.8rem;background:#173247;color:#fff;border:none;border-radius:14px;font-size:.88rem;font-weight:850;cursor:pointer;transition:all .2s ease}
.send-btn-modern:hover:not(:disabled){background:#244b67;transform:translateY(-1px);box-shadow:0 4px 12px rgba(23,50,71,.15)}
.send-btn-modern:disabled{opacity:.4;cursor:not-allowed}
.status-indicators{display:flex;align-items:center;min-width:4.4rem;justify-content:flex-end}
.recording-pulse{display:flex;align-items:center;gap:.4rem;color:#ef4444;font-size:.8rem;font-weight:800;white-space:nowrap}
.pulse-dot{width:8px;height:8px;background:#ef4444;border-radius:50%;animation:dotPulse 1s infinite}
@keyframes dotPulse{0%{transform:scale(0.8);opacity:0.5}50%{transform:scale(1.2);opacity:1}100%{transform:scale(0.8);opacity:0.5}}
.transcribing-spin{display:flex;align-items:center;gap:.4rem;color:#173247;font-size:.8rem;font-weight:800;white-space:nowrap}
.progress-card-modern{margin-top:1rem;padding:1rem 1.1rem;background:linear-gradient(180deg,#f8fbff,#f2f6fb);border-radius:16px;border:1px solid rgba(23,50,71,.12);color:#173247;box-shadow:0 4px 12px rgba(23,50,71,.05)}
.progress-info-modern{display:flex;justify-content:space-between;align-items:center;margin-bottom:.55rem}
.task-label{font-size:.9rem;font-weight:800;letter-spacing:.01em;color:#173247}
.task-percent{font-size:1rem;font-weight:900;font-variant-numeric:tabular-nums;color:#334155}
.progress-bar-track-modern{height:.42rem;background:rgba(23,50,71,.13);border-radius:99px;overflow:hidden;margin-bottom:.45rem}
.progress-bar-fill-modern{height:100%;background:linear-gradient(90deg,#6366f1,#818cf8);box-shadow:0 0 15px rgba(99,102,241,0.5);transition:width .4s cubic-bezier(.23,1,.32,1)}
.task-detail-modern{font-size:.78rem;color:#5f7384;font-weight:600;line-height:1.4}
.mini-spinner-dark{width:14px;height:14px;border:2px solid rgba(23,50,71,.1);border-top-color:#173247;border-radius:50%;animation:spin .8s linear infinite}
.deliverable-grid{grid-template-columns:repeat(3,minmax(0,1fr))}
.choice-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.deliverable-card,.knowledge-card,.history-card,.version-card,.choice-chip{text-align:left;padding:1rem}.deliverable-card.active,.knowledge-card.active,.history-card.active,.version-card.active,.choice-chip.active{background:rgba(57,108,83,.08);border-color:rgba(57,108,83,.28)}.deliverable-card.active{background:linear-gradient(145deg,#295843,#1f4734);color:#fffdf8}
.resource-list,.knowledge-list,.history-list,.version-list{display:flex;flex-direction:column;gap:.75rem}.resource-item,.preview-outline-card,.preview-mini-card{padding:1rem}.resource-item-grid,.summary-grid,.summary-preview-grid{grid-template-columns:repeat(2,minmax(0,1fr))}
.assistant-thread{display:flex;flex-direction:column;gap:1rem;min-height:18rem;max-height:26rem;overflow-y:auto;padding:1.35rem 1.4rem;background:#fff}
.chat-row{display:flex;align-items:flex-start;gap:.8rem}
.chat-row.user{justify-content:flex-end}
.chat-avatar{display:flex;align-items:center;justify-content:center;flex-shrink:0;width:2.3rem;height:2.3rem;border-radius:999px;overflow:hidden}
.chat-avatar.ai{background:transparent}
.chat-avatar-image{width:100%;height:100%;object-fit:cover}
.chat-bubble{max-width:80%;padding:1rem 1.15rem;border-radius:18px;line-height:1.65}
.chat-bubble.assistant{background:#f1f3f5;color:#173247}
.chat-bubble.user{align-self:flex-end;background:linear-gradient(145deg,#173247,#28526e);color:#fffdf8}
.chat-role{margin-bottom:.35rem;font-size:.75rem;font-weight:700;text-transform:uppercase;letter-spacing:.06em;color:inherit}
.chat-copy{display:flex;flex-direction:column;gap:.42rem}
.assistant-checklist{display:flex;flex-direction:column;gap:.68rem;margin-top:.85rem;padding-top:.85rem;border-top:1px dashed rgba(23,50,71,.12)}
.assistant-check-item{display:grid;grid-template-columns:1.6rem minmax(0,1fr);gap:.7rem;align-items:flex-start}
.assistant-check-icon{display:inline-flex;align-items:center;justify-content:center;width:1.45rem;height:1.45rem;border-radius:999px}
.assistant-check-icon svg{width:1rem;height:1rem}
.assistant-check-icon.status-done{background:rgba(44,112,78,.12);color:#2f7d59}
.assistant-check-icon.status-pending{background:rgba(213,147,44,.12);color:#c18416}
.assistant-check-copy{display:flex;flex-direction:column;gap:.1rem;min-width:0}
.assistant-check-copy strong{font-size:.94rem;font-weight:780;line-height:1.35;color:#173247}
.assistant-check-copy span{font-size:.88rem;line-height:1.58;color:#5f7384}
.assistant-followup-note{margin-top:.9rem;padding:.8rem .9rem;border-radius:14px;background:rgba(255,255,255,.82);border:1px solid rgba(23,50,71,.08);font-size:.9rem;line-height:1.6;color:#26445b}
.assistant-inline-hints{display:flex;flex-wrap:wrap;gap:.55rem;margin-top:.8rem}
.hint-chip,.tag,.missing-chip{display:inline-flex;align-items:center;padding:.45rem .75rem;border-radius:999px;font-size:.84rem}.missing-chip{background:rgba(178,59,46,.08);color:#8a3429}
.followup-card{margin-top:1rem;padding:1rem;border:1px solid rgba(23,50,71,.09);border-radius:20px;background:#f8fbfd}
.generation-progress-card{display:flex;flex-direction:column;gap:.7rem;margin-top:1rem;padding:.95rem 1rem;border:1px solid rgba(36,86,120,.12);border-radius:18px;background:linear-gradient(180deg,rgba(248,251,253,.98),rgba(244,248,252,.96));box-shadow:0 8px 20px rgba(23,50,71,.05)}
.generation-progress-card--embedded{margin-top:0}
.generation-progress-card--compact{margin-top:.9rem;margin-bottom:.95rem}
.generation-progress-copy{display:flex;flex-wrap:wrap;align-items:center;justify-content:space-between;gap:.45rem .9rem}
.generation-progress-copy strong{font-size:.94rem;font-weight:760;color:#173247}
.generation-progress-copy span{font-size:.84rem;color:#6d8090;line-height:1.55}
.generation-progress-track{position:relative;overflow:hidden;width:100%;height:.56rem;border-radius:999px;background:rgba(23,50,71,.09)}
.generation-progress-fill{display:block;height:100%;border-radius:inherit;background:linear-gradient(90deg,#244b67,#4d7ca1 60%,#84aeca);box-shadow:0 0 0 1px rgba(255,255,255,.18) inset;transition:width .45s ease}
.generation-progress-meta{display:flex;align-items:center;justify-content:space-between;gap:.75rem;font-size:.78rem;color:#6d8090}
.generation-progress-meta strong{font-size:.82rem;font-weight:760;color:#173247}
.summary-grid dt,.summary-empty,.empty-mini-card,.mini-note,.resource-item-meta,.resource-status,.history-card-meta,.history-card-badge,.preview-outline-head span,.preview-mini-card p,.sources-strip li{font-size:.86rem}.summary-grid dd{margin-top:.25rem;font-size:.96rem;font-weight:600}.summary-stat{padding:.75rem .9rem;border-radius:14px;background:#f5f8fa;font-weight:600}
.editable-grid{grid-template-columns:repeat(2,minmax(0,1fr))}.full-span{grid-column:1 / -1}
.editable-card-modern .summary-card-header{margin-bottom:.9rem}
.editable-card-modern .summary-card-header h4{margin:0}
.editable-grid-modern{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:1rem 1.1rem;align-items:start}
.editable-card-modern .field-group-modern{display:flex;flex-direction:column;gap:.56rem;min-width:0}
.editable-card-modern .field-group-modern.full-span{grid-column:1 / -1}
.field-label-modern{display:flex;align-items:center;gap:.45rem;font-size:.84rem;font-weight:800;line-height:1.38;color:#334155}
.field-label-modern svg{flex-shrink:0;color:#64748b}
.field-label-modern em{font-style:normal;color:#b23b2e}
.editable-card-modern .planner-input-modern,
.editable-card-modern .planner-select-modern{height:2.6rem}
.planner-textarea-modern{width:100%;padding:.66rem .78rem;border:1px solid rgba(23,50,71,.12);border-radius:10px;background:#fff;font-size:.85rem;font-weight:700;color:#173247;line-height:1.55;outline:none;transition:all .2s ease}
.planner-textarea-modern:focus{border-color:#6366f1;box-shadow:0 0 0 3px rgba(99,102,241,.08)}
.editable-card-modern .planner-textarea-modern{min-height:5.8rem}
.dual-input-modern{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:.6rem}
.choice-grid-modern{display:flex;flex-wrap:wrap;gap:.55rem}
.choice-chip-modern{display:inline-flex;align-items:center;justify-content:center;min-height:2.1rem;padding:0 .75rem;border:1px solid rgba(23,50,71,.12);border-radius:999px;background:#fff;color:#516273;font-size:.82rem;font-weight:700;cursor:pointer;transition:all .2s ease}
.choice-chip-modern:hover{border-color:rgba(99,102,241,.35);color:#1f3a50;background:rgba(99,102,241,.05)}
.choice-chip-modern.active{border-color:#6366f1;background:rgba(99,102,241,.1);color:#3f46bb}
.result-empty-state{display:flex;flex-direction:column;align-items:center;justify-content:center;min-height:28rem;gap:1rem;padding:2rem;color:rgba(20,50,73,.68)}.spinner{width:3rem;height:3rem;border-radius:999px;border:4px solid rgba(20,50,73,.12);border-top-color:rgba(20,50,73,.88);animation:spin .9s linear infinite}
.result-empty-state--blank{min-height:46rem;padding:0}
.preview-tabs{display:flex;flex-wrap:wrap;gap:.65rem;padding:1.25rem 1.5rem 0}.preview-outline-card ul{margin-top:.75rem;list-style:disc;padding-left:1.2rem}.sources-strip{border-top:1px solid rgba(20,50,73,.08)}
.resource-status.success{color:#206642}.resource-status.warn{color:#995d0b}.full-width{width:100%}.markdown-pane{padding-top:.5rem}.history-overlay{display:block;position:fixed;inset:0;background:rgba(20,50,73,.22);z-index:20}
.step-form-card{overflow:hidden;border-color:rgba(23,50,71,.10);background:#fff}
.step-form-card .stage-header{display:flex;align-items:flex-start;justify-content:space-between;gap:1rem;padding:1.1rem 1.55rem 1rem;background:#fff;border-bottom:1px solid rgba(23,50,71,.08)}
.step-form-card .stage-header>div{display:flex;flex-direction:column;gap:.65rem}
.stage-header-actions{display:flex;align-items:center;justify-content:flex-end;flex-shrink:0}
.step-form-card .stage-header h3{font-size:1.58rem;font-weight:770;line-height:1.08;letter-spacing:.01em;color:#173247}
.step-form-card .field-label{font-size:.76rem;font-weight:800;letter-spacing:.08em;color:#6d8090}
.step-form-card .planner-input,.step-form-card .planner-select{min-height:3.55rem;padding:.88rem 1rem;font-size:.95rem;border-radius:15px}
.step-form-card .compact-input,.step-form-card .compact-select,.step-form-card .compact-textarea{padding:.82rem .94rem;border-radius:15px;font-size:.93rem}
.step-form-card .compact-input,.step-form-card .compact-select{min-height:3.2rem}
.step-form-card .compact-select{padding-right:2.8rem;background-position:right .9rem center}
.step-form-card .planner-textarea{padding:.92rem 1rem;font-size:.95rem;border-radius:15px;line-height:1.65}
.step-form-card .stage-footer{margin-top:1.55rem;padding:1.1rem 1.55rem 1.3rem;border-top:1px solid rgba(23,50,71,.08)}
.step-one-card .stage-form-grid,.step-one-card .field-block{padding-inline:1.55rem}
.step-one-card .stage-form-grid{padding-top:1.45rem;gap:1.1rem}
.step-one-card .field-block{margin-top:1.25rem;gap:.75rem}
.resource-card{border-color:rgba(23,50,71,.10);background:#fff;box-shadow:0 10px 24px rgba(23,50,71,.05)}
.resource-card-head{padding-bottom:1rem;border-bottom:1px solid rgba(23,50,71,.08)}
.resource-card-head h4{font-size:.98rem;font-weight:760;color:#173247}
.resource-card-head p{margin-top:.3rem;color:#6d8090;font-size:.86rem;line-height:1.58}
.resource-item{border-color:rgba(23,50,71,.08);background:#fff}
.resource-item-title,.knowledge-card-title,.history-card-title{font-weight:720;color:#173247}
.resource-item-meta,.knowledge-card-meta,.history-card-meta{color:#83929e}
.knowledge-card,.history-card,.version-card,.preview-outline-card,.preview-mini-card{border-color:rgba(23,50,71,.08);background:linear-gradient(180deg,#fff,#f8fbfc)}
.step-resource-card{display:flex;flex-direction:column;min-height:38rem}
.step-resource-card .stage-header{padding-bottom:.35rem;border-bottom:none}
.step-resource-card .resource-columns{grid-template-columns:1fr;flex:1;align-content:start;width:100%;margin:0;padding:0 1.55rem;gap:1rem}
.workspace-grid--breakout .step-resource-card .resource-columns{width:100%;margin:0;max-width:none}
.step-resource-card .resource-card{width:100%;padding:1.4rem 1.4rem 1.3rem;border:none;border-radius:28px;background:linear-gradient(180deg,#f7fbff,#f2f7fb);box-shadow:inset 0 1px 0 rgba(255,255,255,.7)}
.step-resource-card .resource-card-head{padding-bottom:.95rem;border-bottom:1px solid rgba(23,50,71,.08)}
.step-resource-card .resource-card-head h4{font-size:1.02rem}
.step-resource-card .resource-card-head p{max-width:26rem;color:#7a8d9c}
.knowledge-picker{display:flex;flex-direction:column;gap:.85rem}
.knowledge-picker-trigger{display:flex;align-items:center;justify-content:space-between;gap:1rem;width:100%;padding:.95rem 1rem;border:1px solid rgba(23,50,71,.10);border-radius:18px;background:rgba(255,255,255,.92);color:#173247;font-weight:720;text-align:left;transition:border-color .18s ease,box-shadow .18s ease,background .18s ease}
.knowledge-picker-trigger strong{font-size:.82rem;color:#597286}
.knowledge-picker-trigger:hover:not(:disabled),.knowledge-picker-trigger.active{border-color:rgba(38,92,120,.28);box-shadow:0 10px 22px rgba(23,50,71,.08);background:#fff}
.knowledge-picker-trigger:disabled{opacity:.62;cursor:not-allowed}
.knowledge-picker-panel{display:flex;flex-direction:column;gap:.8rem;padding:1rem;border:1px solid rgba(23,50,71,.08);border-radius:20px;background:rgba(255,255,255,.82)}
.knowledge-search-input{background:#fff}
.knowledge-option-list{display:flex;flex-direction:column;gap:.6rem;max-height:18rem;overflow:auto;padding-right:.2rem}
.knowledge-option{display:flex;align-items:center;justify-content:space-between;gap:1rem;padding:.9rem 1rem;border:1px solid rgba(23,50,71,.08);border-radius:16px;background:linear-gradient(180deg,#fff,#f8fbfc);text-align:left;transition:border-color .18s ease,transform .18s ease,box-shadow .18s ease}
.knowledge-option:hover{transform:translateY(-1px);box-shadow:0 12px 22px rgba(23,50,71,.06)}
.knowledge-option.active{border-color:rgba(38,92,120,.28);background:rgba(23,50,71,.08)}
.knowledge-option-copy{display:flex;flex-direction:column;gap:.3rem;min-width:0}
.knowledge-option-title{font-weight:720;color:#173247;word-break:break-all}
.knowledge-option-meta{font-size:.84rem;color:#7a8d9c}
.knowledge-option-check{flex-shrink:0;font-size:.82rem;font-weight:700;color:#33536f}
.knowledge-selected-tags{margin-top:.95rem}
.step-resource-card .knowledge-card{padding:.95rem 1rem;border:1px solid rgba(23,50,71,.08);border-radius:16px;background:rgba(255,255,255,.82);box-shadow:none}
.step-resource-card .knowledge-card.active{background:rgba(23,50,71,.08);border-color:transparent}
.step-resource-card .knowledge-card.disabled{opacity:.56;box-shadow:none}
.step-resource-card .resource-item{padding:1.1rem 1.05rem;border:1px solid rgba(23,50,71,.08);border-radius:20px;background:#fff;box-shadow:0 12px 24px rgba(23,50,71,.04)}
.step-resource-card .empty-mini-card{padding:1.35rem 1.05rem;border:1px solid rgba(23,50,71,.08);border-radius:18px;background:rgba(255,255,255,.82);color:#6d8090}
.step-resource-card .resource-list,.step-resource-card .knowledge-list{gap:.6rem}
.step-resource-card .resource-actions{margin-top:.1rem}
.step-resource-card .resource-status{font-size:.84rem}
.step-resource-card .resource-item-head{align-items:flex-start}
.resource-file-meta{display:flex;align-items:flex-start;gap:.9rem;min-width:0}
.resource-file-icon{display:inline-flex;align-items:center;justify-content:center;flex-shrink:0;width:2.8rem;height:2.8rem;border-radius:14px;background:linear-gradient(145deg,#eef5fb,#dfeaf5);border:1px solid rgba(58,93,126,.12);font-size:.72rem;font-weight:800;letter-spacing:.04em;color:#33536f}
.step-resource-card .resource-item-title{font-size:1.02rem;font-weight:780;line-height:1.35}
.step-resource-card .resource-item-meta{margin-top:.22rem;word-break:break-all}
.step-resource-card .resource-item-grid{gap:.9rem 1rem;margin-top:.95rem}
.field-helper{font-size:.78rem;line-height:1.5;color:#7a8d9c}
.field-helper--error{color:#b23b2e;font-weight:650}
.resource-step-guide{display:flex;flex-wrap:wrap;align-items:flex-start;gap:.5rem .75rem;margin:1rem 1.55rem 0;padding:.95rem 1rem;border:1px solid rgba(44,112,78,.18);border-radius:18px;background:linear-gradient(180deg,rgba(239,249,243,.92),rgba(247,251,248,.98));color:#295843}
.resource-step-guide strong{font-size:.86rem;font-weight:780;letter-spacing:.02em}
.resource-step-guide span{font-size:.85rem;line-height:1.6;color:#48675a}
.resource-step-guide.warn{border-color:rgba(178,114,31,.22);background:linear-gradient(180deg,rgba(255,247,236,.96),rgba(255,251,245,.98));color:#8a5b2c}
.resource-step-guide.warn span{color:#85684b}
.planner-primary-button:disabled,.planner-ghost-button:disabled,.planner-export-button:disabled{opacity:.56;cursor:not-allowed;box-shadow:none;transform:none}
.step-resource-card .planner-input.is-invalid,.step-resource-card .planner-select.is-invalid{border-color:rgba(178,59,46,.4);background:#fff7f5;box-shadow:0 0 0 3px rgba(178,59,46,.08)}
.step-resource-card .planner-input.is-invalid:focus,.step-resource-card .planner-select.is-invalid:focus{border-color:rgba(178,59,46,.55);box-shadow:0 0 0 4px rgba(178,59,46,.12)}
.step-requirement-card .assistant-stage{padding:1.15rem 1.55rem 1.3rem}
.step-requirement-card .assistant-thread--embedded{min-height:13rem;max-height:none;padding:0 0 1rem;background:transparent;border-bottom:1px solid rgba(23,50,71,.08)}
.step-requirement-card .assistant-hints{display:flex;flex-wrap:wrap;align-items:center;gap:.7rem}
.step-requirement-card .assistant-compose--embedded{padding:1rem 0 0;background:transparent}
.step-requirement-card .assistant-input-shell{position:relative}
.step-requirement-card .assistant-textarea{min-height:8.8rem;border-radius:18px;padding-right:8.25rem;padding-bottom:4rem}
.step-requirement-card .assistant-inline-actions{position:absolute;right:1rem;bottom:1rem;display:flex;align-items:center;gap:.55rem}
.step-requirement-card .assistant-icon-button{display:inline-flex;align-items:center;justify-content:center;width:2.9rem;height:2.9rem;border:1px solid rgba(23,50,71,.12);border-radius:999px;background:#fff;color:#23465d;box-shadow:0 8px 18px rgba(23,50,71,.08);transition:transform .18s ease,box-shadow .18s ease,background .18s ease,color .18s ease,border-color .18s ease}
.step-requirement-card .assistant-icon-button svg{width:1.2rem;height:1.2rem}
.step-requirement-card .assistant-icon-button:hover:not(:disabled){transform:translateY(-1px);border-color:rgba(23,50,71,.22);box-shadow:0 12px 24px rgba(23,50,71,.12)}
.step-requirement-card .assistant-icon-button:disabled{opacity:.46;cursor:not-allowed;box-shadow:none}
.step-requirement-card .assistant-icon-button--primary{background:linear-gradient(135deg,#163247,#2b5b79);border-color:#163247;color:#fffdf8}
.step-requirement-card .assistant-icon-button--warn{color:#b23b2e}
.step-requirement-card .assistant-compose-actions{display:flex;flex-direction:column;align-items:stretch;gap:.75rem;margin-top:.75rem}
.step-requirement-card .assistant-status-row{display:flex;justify-content:flex-end;gap:.7rem;min-height:1.25rem}
.step-requirement-card .hint-chip{background:#fff;border-color:rgba(23,50,71,.12);color:#26445b}
.step-requirement-card .hint-chip:hover{border-color:rgba(23,50,71,.22);background:#f8fafc}
.step-requirement-card .choice-chip{background:#fff;border-color:rgba(23,50,71,.10);color:#5f7384}
.step-requirement-card .choice-chip.active{background:rgba(23,50,71,.06);border-color:rgba(23,50,71,.18);color:#173247}
.result-main-panel,.result-side-panel,.result-preview-card{border-color:rgba(23,50,71,.09);background:#fff}
.history-rail{border-color:rgba(185,135,78,.14);background:linear-gradient(180deg,#fffdf9,#f8f1e6)}
.history-rail-head{background:linear-gradient(180deg,#fffdf8,#f7efe3);border-bottom-color:rgba(170,120,64,.12)}
.history-rail-head h3{color:#8a5b2c}
.preview-tabs{background:#fff}
.summary-panel{display:flex;flex-direction:column;gap:1.2rem;min-width:0}
.summary-panel-head{display:flex;align-items:center;justify-content:space-between;padding:1.5rem;border:1px solid rgba(23,50,71,.08);border-radius:24px;background:#fff;box-shadow:0 10px 30px rgba(23,50,71,.04);transition:all .3s ease}
.summary-header-main{display:flex;flex-direction:column;gap:.35rem}
.summary-badge{display:inline-flex;padding:.3rem .7rem;background:rgba(99,102,241,.1);color:#6366f1;border-radius:99px;font-size:.65rem;font-weight:800;text-transform:uppercase;letter-spacing:.12em;width:fit-content}
.summary-panel-head h3{font-size:1.25rem;font-weight:850;color:#173247;letter-spacing:-.01em}
.summary-hint{font-size:.8rem;color:#6d8090}
.summary-toggle-btn{display:flex;align-items:center;justify-content:center;width:2.5rem;height:2.5rem;border-radius:50%;background:rgba(23,50,71,.05);color:#6d8090;transition:all .3s cubic-bezier(.23,1,.32,1)}
.summary-toggle-btn:hover{background:rgba(99,102,241,.1);color:#6366f1}
.summary-toggle-btn.active{transform:rotate(-90deg);background:#6366f1;color:#fff}
.summary-panel-body{display:grid;grid-template-rows:1fr;overflow:hidden;transition:grid-template-rows .3s cubic-bezier(.23,1,.32,1),opacity .2s ease,margin-top .2s ease}
.summary-panel-body.collapsed{grid-template-rows:0fr;opacity:0;margin-top:-.5rem;pointer-events:none}
.summary-panel-body-inner{min-height:0;display:flex;flex-direction:column;gap:1rem;overflow:hidden}
.workspace-grid .summary-card,.workspace-grid .editable-card{padding:1.5rem;border-radius:24px;border:1px solid rgba(23,50,71,.06);background:#fff;box-shadow:0 4px 12px rgba(23,50,71,.02)}
.summary-readonly-card h4,.editable-card h4{font-size:.9rem;font-weight:850;color:#173247;text-transform:uppercase;letter-spacing:.08em;margin-bottom:1.2rem;display:flex;align-items:center;gap:.6rem}
.summary-readonly-card h4::before{content:'';width:4px;height:14px;background:#6366f1;border-radius:2px}
.summary-grid dt{font-size:.65rem;font-weight:800;text-transform:uppercase;letter-spacing:.1em;color:#94a3b8;margin-bottom:.35rem}
.summary-grid dd{font-size:1rem;font-weight:700;color:#173247;line-height:1.4}
.summary-grid dd.empty{color:#cbd5e1;font-weight:500;font-style:italic}
.summary-readonly-card .summary-grid>div{padding:1rem;border-radius:16px;background:rgba(23,50,71,.02);border:1px solid transparent;transition:all .2s ease}
.summary-readonly-card .summary-grid>div:hover{background:#fff;border-color:rgba(99,102,241,.15);box-shadow:0 8px 16px rgba(23,50,71,.03)}
.step-one-card .stage-header-content{display:flex;flex-direction:column;gap:.4rem}
.step-one-card .stage-header h3{font-size:1.8rem;font-weight:900;letter-spacing:-.02em;color:#173247;margin:0}
.step-one-card .stage-header p{color:#64748b;font-size:.95rem;margin:0}
.field-icon{margin-right:6px;color:#6366f1;vertical-align:middle;opacity:.8}
.planner-select:focus,.planner-input:focus,.planner-textarea:focus{border-color:#6366f1;box-shadow:0 0 0 4px rgba(99,102,241,.1);background:#fff}
.step-one-card .deliverable-grid{grid-template-columns:repeat(3,1fr);gap:1.2rem}
.step-one-card .deliverable-card{position:relative;display:flex;flex-direction:column;align-items:center;text-align:center;gap:1.2rem;padding:2rem 1.5rem;border:1px solid rgba(23,50,71,.08);border-radius:24px;background:#fff;box-shadow:0 4px 20px rgba(23,50,71,.03);transition:all .4s cubic-bezier(.23,1,.32,1);overflow:hidden}
.deliverable-card-icon{display:flex;align-items:center;justify-content:center;width:3.5rem;height:3.5rem;border-radius:16px;background:rgba(23,50,71,.04);color:#173247;transition:all .3s ease}
.deliverable-card-content{display:flex;flex-direction:column;gap:.5rem}
.deliverable-card-title{font-size:1.15rem;font-weight:850;color:#173247}
.deliverable-card-body{font-size:.85rem;color:#64748b;line-height:1.5}
.deliverable-check{position:absolute;top:1.2rem;right:1.2rem;width:1.6rem;height:1.6rem;border-radius:50%;border:2px solid rgba(23,50,71,.1);display:flex;align-items:center;justify-content:center;color:transparent;transition:all .3s ease;background:#fff}
.deliverable-card:hover{transform:translateY(-5px);border-color:rgba(99,102,241,.2);box-shadow:0 15px 30px rgba(99,102,241,.06)}
.deliverable-card:hover .deliverable-card-icon{background:rgba(99,102,241,.08);color:#6366f1;transform:scale(1.1)}
.deliverable-card.active{border-color:#6366f1;background:rgba(99,102,241,.02)}
.deliverable-card.active .deliverable-card-icon{background:#6366f1;color:#fff;box-shadow:0 8px 16px rgba(99,102,241,.25)}
.deliverable-card.active .deliverable-check{background:#6366f1;border-color:#6366f1;color:#fff;box-shadow:0 4px 10px rgba(99,102,241,.2)}
.planner-primary-button{background:linear-gradient(135deg,#6366f1,#4f46e5);color:#fff;border:none;box-shadow:0 10px 25px rgba(99,102,241,.25);transition:all .3s ease}
.planner-primary-button:hover:not(:disabled){transform:translateY(-2px);box-shadow:0 15px 30px rgba(99,102,241,.35);background:linear-gradient(135deg,#4f46e5,#4338ca)}
.planner-ghost-button{color:#64748b;border-color:rgba(23,50,71,.1);background:transparent;transition:all .2s ease}
.planner-ghost-button:hover:not(:disabled){color:#173247;background:rgba(23,50,71,.05);border-color:rgba(23,50,71,.2)}
.step-one-card .choice-chip{background:#fff;border-color:rgba(57,108,83,.14);color:#567463}
.field-hint{font-size:.84rem;line-height:1.55;color:#6d8090}
.result-toolbar{background:linear-gradient(180deg,#fff,#f8fbfc)}
.result-toolbar-status{color:#5f7384}
.preview-tab{color:#657887}
@keyframes spin{to{transform:rotate(360deg)}}
@media (max-width:1279px){.planner-frame--breakout::after{display:none}.workspace-grid,.result-grid,.workspace-grid--breakout,.result-grid--breakout{grid-template-columns:1fr;width:auto;margin-right:0}.summary-panel{order:-1}.workspace-grid--breakout .summary-panel,.result-grid--breakout .result-side-panel{width:auto}.result-grid--preview,.result-grid--history,.result-grid--history-detail{row-gap:1rem}.result-format-rail,.history-rail--docked{position:static;left:auto;top:auto;flex-direction:row;flex-wrap:wrap;width:auto;padding-top:0}.result-main-panel--history-preview{padding-left:0}.history-preview-rail{position:static;flex-direction:row;flex-wrap:wrap;width:auto;margin-bottom:1rem}.history-library-shell{padding-left:1rem;padding-right:1rem}.history-card--library{width:100%}.result-grid--history-detail.result-grid--breakout{width:auto;margin-left:0;margin-right:0;padding-left:0}}
@media (max-width:1023px){.planner-header{flex-direction:column}.planner-header-main,.planner-compact-bar{flex-direction:column;align-items:stretch}.planner-actions,.planner-actions--full,.planner-actions--inline{justify-content:flex-start}.planner-steprail{padding-top:0}.step-chip{min-width:9.2rem}.planner-compact-bar--teleported{grid-template-columns:1fr;width:100%;margin-left:0}.launcher-grid{grid-template-columns:1fr;max-width:32rem}.resource-columns,.resource-columns-modern,.stage-form-grid,.editable-grid,.editable-grid-modern,.summary-preview-grid,.resource-item-grid,.grade-grid,.deliverable-grid,.choice-grid,.summary-grid{grid-template-columns:1fr}.step-form-card .stage-header{flex-direction:column}.stage-header-actions{width:100%;justify-content:flex-start}.step-resource-card .resource-columns{padding-left:1.25rem;padding-right:1.25rem}.step-requirement-card .assistant-stage{padding-left:1.25rem;padding-right:1.25rem}.result-grid{padding-left:1rem;padding-right:1rem}.result-preview-toolbar{flex-direction:column;align-items:stretch}.result-preview-toolbar-actions{justify-content:flex-start}.result-preview-body{min-height:34rem}.result-material-preview :deep(.preview-body){min-height:34rem}.history-overlay{display:block;position:fixed;inset:0;background:rgba(20,50,73,.22);z-index:20}.history-rail{position:fixed;top:0;left:0;width:min(22rem,88vw);height:100vh;z-index:30;transform:translateX(-105%);transition:transform .2s ease;border-radius:0 24px 24px 0}.history-rail.open{transform:translateX(0)}.chat-thread-container{height:500px}}
@media (max-width:1023px){.planner-modal-backdrop{padding:1rem}.planner-modal-actions{flex-direction:column-reverse}.planner-danger-button,.planner-modal-close,.planner-modal-actions .planner-ghost-button{width:100%}}
@media (max-width:767px){.planner-header,.launcher-stage,.workspace-grid{padding-left:1rem;padding-right:1rem}.planner-steprail{padding-top:0;gap:.55rem}.planner-title{font-size:1.7rem}.step-chip{min-width:auto;padding:.72rem .88rem}.step-chip-label{font-size:.96rem}.planner-compact-bar--teleported .flow-step{font-size:.8rem}.planner-compact-bar--teleported .planner-actions{gap:.45rem}.planner-compact-bar--teleported .planner-ghost-button,.planner-compact-bar--teleported .planner-primary-button,.planner-compact-bar--teleported .planner-export-button{font-size:.82rem}.chat-bubble{max-width:100%}.step-form-card .stage-header,.step-form-card .stage-footer,.step-one-card .stage-form-grid,.step-one-card .field-block,.step-resource-card .resource-columns,.step-requirement-card .assistant-stage{padding-left:1rem;padding-right:1rem}.step-form-card .stage-header h3{font-size:1.46rem}.step-form-card .planner-input,.step-form-card .planner-select{min-height:3.45rem;font-size:.94rem}.summary-panel-head h3{font-size:1.12rem}.workspace-grid .summary-card,.workspace-grid .editable-card{padding:1rem}.textarea-wrapper-modern{padding:.5rem .55rem .5rem .8rem;gap:.55rem}.compose-actions-modern{gap:.5rem}.status-indicators{min-width:auto}.recording-pulse,.transcribing-spin{font-size:.74rem}.send-btn-modern{padding:0 1rem}.send-btn-modern span{display:none}.chat-thread-container{height:420px}}
</style>
