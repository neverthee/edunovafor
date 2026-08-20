<template>
  <div class="flex flex-col h-full bg-white">
    <!-- Header -->
    <div class="flex items-center justify-between border-b border-gray-100 px-8 py-5">
      <div>
        <h2 class="text-xl font-medium text-gray-800">{{ assessment.id ? '编辑评估' : '创建评估' }}</h2>
        <p class="mt-1 text-sm text-gray-500">先填写最基本的信息，其他设置可选。</p>
      </div>
      <button @click="$emit('cancel')" class="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors">
        <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
        </svg>
      </button>
    </div>

    <!-- Body -->
    <div class="flex-1 overflow-y-auto px-8 py-6 custom-scrollbar">
      <form @submit.prevent="handleSubmit" class="mx-auto max-w-4xl space-y-10">
        
        <!-- 基本信息部分 -->
        <div class="space-y-6">
          <div class="grid grid-cols-1 gap-6 md:grid-cols-2">
            <div class="md:col-span-2">
              <label class="mb-1.5 block text-sm font-medium text-gray-700">评估标题</label>
              <input 
                v-model="form.title"
                type="text"
                required
                class="block w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                placeholder="输入评估标题"
              />
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">所属课程</label>
              <select
                v-model="form.course_id"
                required
                :disabled="loading"
                class="block w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 disabled:bg-gray-50 disabled:text-gray-500"
              >
                <option value="">选择课程</option>
                <option v-if="loading" value="" disabled>加载中...</option>
                <option v-else-if="courses.length === 0" value="" disabled>暂无可选课程</option>
                <option v-else v-for="course in courses" :key="course.id" :value="course.id">
                  {{ course.name }}
                </option>
              </select>
              <p v-if="courses.length === 0 && !loading" class="mt-1.5 text-xs text-amber-500">
                请先在课程管理中创建课程
              </p>
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">总分</label>
              <input
                v-model.number="form.total_score"
                type="number"
                required
                min="0"
                class="block w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
              />
            </div>

            <div class="md:col-span-2">
              <label class="mb-1.5 block text-sm font-medium text-gray-700">所属章节 <span class="text-gray-400 font-normal">（可选）</span></label>
              <select
                v-model="selectedChapterId"
                :disabled="!form.course_id || chaptersLoading || chapters.length === 0"
                class="block w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 disabled:bg-gray-50 disabled:text-gray-500"
              >
                <option value="">{{ chaptersLoading ? '章节加载中...' : '不限定章节' }}</option>
                <option v-for="chapter in chapters" :key="chapter.id" :value="chapter.id">
                  {{ chapter.title }}
                </option>
              </select>
              <p class="mt-1.5 text-xs text-gray-500">
                选择后，AI 生成会优先参考该章节对应的课件页内容；不选则按整门课程生成。
              </p>
            </div>

            <div class="md:col-span-2">
              <label class="mb-1.5 block text-sm font-medium text-gray-700">描述</label>
              <textarea
                v-model="form.description"
                rows="3"
                class="block w-full rounded-lg border border-gray-200 px-4 py-2.5 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500 resize-none"
                placeholder="一句话说明这份评估做什么即可"
              ></textarea>
            </div>
          </div>
        </div>

        <!-- 高级设置 -->
        <div>
          <button
            type="button"
            @click="showAdvancedSettings = !showAdvancedSettings"
            class="group flex items-center text-sm font-medium text-gray-600 hover:text-purple-600 transition-colors"
          >
            <svg
              class="mr-2 h-4 w-4 transform transition-transform duration-200"
              :class="showAdvancedSettings ? 'rotate-90 text-purple-600' : 'text-gray-400 group-hover:text-purple-600'"
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
            </svg>
            高级设置
          </button>

          <div v-show="showAdvancedSettings" class="mt-6 grid grid-cols-1 gap-6 md:grid-cols-2 rounded-xl bg-gray-50/50 p-6 border border-gray-100">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">时间限制 <span class="text-gray-400 font-normal">（分钟）</span></label>
              <input
                v-model.number="form.duration"
                type="number"
                min="0"
                class="block w-full rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                placeholder="不填则无限制"
              />
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">最大尝试次数</label>
              <input
                v-model.number="form.max_attempts"
                type="number"
                min="0"
                class="block w-full rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                placeholder="不填则无限制"
              />
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">开始时间</label>
              <input
                v-model="form.start_date"
                type="datetime-local"
                class="block w-full rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
              />
            </div>

            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">截止时间</label>
              <input
                v-model="form.due_date"
                type="datetime-local"
                class="block w-full rounded-lg border border-gray-200 bg-white px-4 py-2 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
              />
            </div>

            <div class="md:col-span-2 pt-2">
              <label class="inline-flex items-center cursor-pointer">
                <input
                  v-model="form.is_active"
                  type="checkbox"
                  class="peer sr-only"
                />
                <div class="h-5 w-9 rounded-full bg-gray-200 transition-colors peer-checked:bg-purple-600 peer-focus:ring-2 peer-focus:ring-purple-500/30 after:absolute after:left-[2px] after:top-[2px] after:h-4 after:w-4 after:rounded-full after:bg-white after:transition-all peer-checked:after:translate-x-4 relative"></div>
                <span class="ml-3 text-sm font-medium text-gray-700">立即发布</span>
              </label>
            </div>
          </div>
        </div>

        <hr class="border-gray-100" />

        <!-- 题目列表 -->
        <div class="space-y-6">
          <div class="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <h3 class="text-lg font-medium text-gray-800">题目列表</h3>
            <div class="flex flex-wrap items-center gap-3">
              <input
                ref="wordFileInput"
                type="file"
                accept=".docx"
                class="hidden"
                @change="handleWordImport"
              />
              <input
                ref="imageFileInput"
                type="file"
                accept="image/png,image/jpeg,image/webp,image/bmp,image/gif"
                class="hidden"
                @change="handleImageImport"
              />
              
              <button
                type="button"
                @click="showAiGenerationModal = true"
                class="inline-flex items-center rounded-lg bg-purple-50 px-3.5 py-2 text-sm font-medium text-purple-700 hover:bg-purple-100 transition-colors"
              >
                <svg class="mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h7z" />
                </svg>
                AI生成
              </button>
              
              <div class="h-4 w-px bg-gray-200 hidden sm:block"></div>
              
              <button
                type="button"
                @click="triggerImageImport"
                :disabled="isImportingImage"
                class="inline-flex items-center text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors disabled:opacity-50"
              >
                <svg class="mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16l4.586-4.586a2 2 0 012.828 0L16 16m-2-2l1.586-1.586a2 2 0 012.828 0L20 14m-6-6h.01M6 20h12a2 2 0 002-2V6a2 2 0 00-2-2H6a2 2 0 00-2 2v12a2 2 0 002 2z" />
                </svg>
                {{ isImportingImage ? '识别中...' : '导图' }}
              </button>
              
              <button
                type="button"
                @click="triggerWordImport"
                :disabled="isImportingWord"
                class="inline-flex items-center text-sm font-medium text-gray-600 hover:text-gray-900 transition-colors disabled:opacity-50"
              >
                <svg class="mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                {{ isImportingWord ? '导入中...' : '导Word' }}
              </button>
              
              <button
                type="button"
                @click="addQuestion"
                class="inline-flex items-center rounded-lg bg-gray-900 px-3.5 py-2 text-sm font-medium text-white hover:bg-gray-800 transition-colors"
              >
                <svg class="mr-1.5 h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
                </svg>
                添加题目
              </button>
            </div>
          </div>

          <div v-if="form.questions.length === 0" class="flex flex-col items-center justify-center py-16 rounded-xl border border-dashed border-gray-200 bg-gray-50/50">
            <svg class="h-10 w-10 text-gray-300 mb-3" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2" />
            </svg>
            <p class="text-sm text-gray-500">暂无题目，可手动添加或导入</p>
          </div>

          <div v-else class="space-y-6">
            <div
              v-for="(question, index) in form.questions"
              :key="index"
              class="group relative rounded-xl border border-gray-100 bg-white p-6 shadow-sm transition-all hover:shadow-md hover:border-gray-200"
            >
              <div class="flex items-center justify-between mb-6">
                <div class="flex items-center space-x-4">
                  <span class="flex h-7 w-7 items-center justify-center rounded-full bg-gray-100 text-xs font-semibold text-gray-600">
                    {{ index + 1 }}
                  </span>
                  <select
                    v-model="question.type"
                    @change="handleQuestionTypeChange(question)"
                    class="block w-36 rounded-lg border-transparent bg-gray-50 py-1.5 pl-3 pr-8 text-sm font-medium text-gray-700 hover:bg-gray-100 focus:border-purple-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-purple-500 transition-colors cursor-pointer"
                  >
                    <option value="multiple_choice">单选题</option>
                    <option value="multiple_answer">多选题</option>
                    <option value="true_false">判断题</option>
                    <option value="fill_blank">填空题</option>
                    <option value="short_answer">简答题</option>
                  </select>
                </div>
                
                <div class="flex items-center space-x-4">
                  <div class="flex items-center space-x-2">
                    <span class="text-sm text-gray-500">分值</span>
                    <input
                      v-model.number="question.score"
                      type="number"
                      min="0"
                      class="w-16 rounded-md border border-gray-200 px-2 py-1 text-center text-sm focus:border-purple-500 focus:outline-none"
                    />
                  </div>
                  <button
                    type="button"
                    @click="removeQuestion(index)"
                    class="text-gray-400 hover:text-red-500 opacity-0 group-hover:opacity-100 transition-opacity"
                    title="删除题目"
                  >
                    <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  </button>
                </div>
              </div>

              <div class="space-y-5">
                <div>
                  <textarea
                    v-model="question.content"
                    rows="2"
                    class="block w-full resize-none rounded-lg border border-gray-200 bg-gray-50/50 px-4 py-3 text-sm transition-colors focus:border-purple-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-purple-500"
                    placeholder="输入题干内容..."
                  ></textarea>
                </div>

                <!-- 选项或答案部分 -->
                <div class="pl-2">
                  <!-- 多选题/单选题选项 -->
                  <div v-if="['multiple_choice', 'multiple_answer'].includes(question.type)" class="space-y-3">
                    <div
                      v-for="(option, optionIndex) in question.options"
                      :key="optionIndex"
                      class="flex items-center space-x-3"
                    >
                      <div class="flex h-5 w-5 items-center justify-center">
                        <input
                          v-if="question.type === 'multiple_choice'"
                          type="radio"
                          :name="`question_${index}`"
                          :value="optionIndex"
                          v-model="question.answer"
                          class="h-4 w-4 cursor-pointer border-gray-300 text-purple-600 focus:ring-purple-500"
                        />
                        <input
                          v-else
                          type="checkbox"
                          :checked="isOptionSelected(question, optionIndex)"
                          @change="toggleAnswerOption(question, optionIndex)"
                          class="h-4 w-4 cursor-pointer rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                        />
                      </div>
                      <input
                        v-model="question.options[optionIndex]"
                        type="text"
                        class="flex-1 rounded-lg border-transparent hover:border-gray-200 focus:border-purple-500 px-3 py-1.5 text-sm transition-colors focus:outline-none focus:bg-white bg-transparent"
                        :placeholder="`选项 ${String.fromCharCode(65 + optionIndex)}`"
                      />
                      <button
                        type="button"
                        @click="removeOption(question, optionIndex)"
                        class="text-gray-300 hover:text-red-500 transition-colors p-1"
                      >
                        <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                        </svg>
                      </button>
                    </div>
                    <button
                      type="button"
                      @click="addOption(question)"
                      class="ml-8 text-sm font-medium text-purple-600 hover:text-purple-700"
                    >
                      + 添加选项
                    </button>
                  </div>

                  <!-- 判断题 -->
                  <div v-else-if="question.type === 'true_false'" class="flex space-x-6">
                    <label class="flex items-center cursor-pointer p-2 rounded-lg hover:bg-gray-50 transition-colors">
                      <input
                        type="radio"
                        v-model="question.answer"
                        :value="true"
                        class="h-4 w-4 border-gray-300 text-purple-600 focus:ring-purple-500"
                      />
                      <span class="ml-2 text-sm font-medium">正确</span>
                    </label>
                    <label class="flex items-center cursor-pointer p-2 rounded-lg hover:bg-gray-50 transition-colors">
                      <input
                        type="radio"
                        v-model="question.answer"
                        :value="false"
                        class="h-4 w-4 border-gray-300 text-purple-600 focus:ring-purple-500"
                      />
                      <span class="ml-2 text-sm font-medium">错误</span>
                    </label>
                  </div>

                  <!-- 填空题 -->
                  <div v-else-if="question.type === 'fill_blank'">
                    <div v-if="!Array.isArray(question.answer)" class="relative">
                      <input
                        v-model="question.answer"
                        type="text"
                        class="block w-full rounded-lg border-b border-gray-200 border-x-0 border-t-0 bg-transparent px-3 py-2 text-sm focus:border-purple-500 focus:ring-0"
                        placeholder="填入正确答案..."
                      />
                      <button 
                        type="button"
                        @click="convertToMultipleAnswers(question)"
                        class="absolute right-0 top-1/2 -translate-y-1/2 text-xs text-purple-600 hover:text-purple-700"
                      >
                        转为多空
                      </button>
                    </div>
                    <div v-else class="space-y-3">
                      <div v-for="(answer, answerIndex) in question.answer" :key="answerIndex" class="flex items-center space-x-3">
                        <span class="text-sm font-medium text-gray-500 w-12 text-right">空 {{ answerIndex + 1 }}</span>
                        <input
                          v-model="question.answer[answerIndex]"
                          type="text"
                          class="flex-1 rounded-lg border-b border-gray-200 border-x-0 border-t-0 bg-transparent px-3 py-1.5 text-sm focus:border-purple-500 focus:ring-0"
                          :placeholder="`填写空 ${answerIndex + 1} 的答案...`"
                        />
                        <button
                          v-if="question.answer.length > 1"
                          type="button"
                          @click="removeAnswer(question, answerIndex)"
                          class="text-gray-300 hover:text-red-500 p-1"
                        >
                          <svg class="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
                          </svg>
                        </button>
                      </div>
                      <div class="flex items-center space-x-4 pl-14">
                        <button
                          type="button"
                          @click="addAnswer(question)"
                          class="text-sm font-medium text-purple-600 hover:text-purple-700"
                        >
                          + 添加空
                        </button>
                        <button 
                          v-if="question.answer.length > 1"
                          type="button"
                          @click="convertToSingleAnswer(question)"
                          class="text-sm font-medium text-gray-500 hover:text-gray-700"
                        >
                          转为单空
                        </button>
                      </div>
                    </div>
                  </div>

                  <!-- 简答题 -->
                  <div v-else-if="question.type === 'short_answer'">
                    <textarea
                      v-model="question.reference_answer"
                      rows="2"
                      class="block w-full resize-none rounded-lg border border-gray-200 bg-transparent px-4 py-3 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
                      placeholder="输入参考答案..."
                    ></textarea>
                  </div>
                </div>

                <!-- 解析 (默认折叠或轻量显示) -->
                <div>
                  <details class="group/details">
                    <summary class="cursor-pointer text-sm font-medium text-gray-500 hover:text-gray-700 list-none flex items-center">
                      <svg class="mr-1.5 h-4 w-4 transform transition-transform group-open/details:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
                      </svg>
                      添加解析
                      <span v-if="question.explanation" class="ml-2 inline-flex h-2 w-2 rounded-full bg-purple-400"></span>
                    </summary>
                    <div class="mt-3">
                      <textarea
                        v-model="question.explanation"
                        rows="2"
                        class="block w-full resize-none rounded-lg border border-gray-200 bg-gray-50 px-4 py-3 text-sm transition-colors focus:border-purple-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-purple-500"
                        placeholder="输入解析内容..."
                      ></textarea>
                    </div>
                  </details>
                </div>
              </div>
            </div>
          </div>
        </div>
      </form>
    </div>

    <!-- Footer Actions -->
    <div class="border-t border-gray-100 bg-white px-8 py-4 flex justify-end space-x-3 rounded-b-lg">
      <button
        type="button"
        @click="$emit('cancel')"
        class="rounded-lg px-5 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors focus:outline-none"
      >
        取消
      </button>
      <button
        type="button"
        @click="handleSubmit"
        class="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 transition-colors focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
      >
        保存评估
      </button>
    </div>

    <!-- 图片导入 Modal -->
    <div v-if="showImageImportModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div class="max-h-[90vh] w-full max-w-5xl overflow-hidden rounded-2xl bg-white shadow-2xl flex flex-col">
        <div class="flex items-center justify-between border-b border-gray-100 px-8 py-5 shrink-0">
          <div>
            <h3 class="text-lg font-medium text-gray-900">确认图片识别结果</h3>
            <p class="mt-1 text-sm text-gray-500">
              {{ imageImportPreview.fileName }}
              <span v-if="imageImportPreview.parseMessage">，{{ imageImportPreview.parseMessage }}</span>
            </p>
          </div>
          <button
            type="button"
            @click="closeImageImportModal"
            class="rounded-full p-2 text-gray-400 hover:bg-gray-100 hover:text-gray-600 transition-colors"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="grid flex-1 grid-cols-1 gap-8 overflow-y-auto px-8 py-6 lg:grid-cols-[300px_minmax(0,1fr)] custom-scrollbar">
          <!-- 图片预览侧边栏 -->
          <div class="space-y-5">
            <div class="overflow-hidden rounded-xl border border-gray-100 bg-gray-50 flex items-center justify-center p-2">
              <img
                v-if="imageImportPreview.previewUrl"
                :src="imageImportPreview.previewUrl"
                alt="识别题目图片"
                class="max-h-[400px] w-full object-contain rounded-lg"
              />
            </div>

            <div v-if="imageImportPreview.ignoredTexts.length" class="rounded-xl border border-amber-100 bg-amber-50/50 p-4">
              <h4 class="text-sm font-medium text-amber-800">忽略信息</h4>
              <ul class="mt-2 space-y-1.5 text-xs text-amber-700/80">
                <li v-for="(item, index) in imageImportPreview.ignoredTexts" :key="`ignored_${index}`" class="line-clamp-2" :title="item">• {{ item }}</li>
              </ul>
            </div>

            <details v-if="imageImportPreview.ocrText" class="group rounded-xl border border-gray-100 bg-gray-50 p-4">
              <summary class="cursor-pointer text-sm font-medium text-gray-600 hover:text-gray-900 list-none flex justify-between items-center">
                查看 OCR 原文
                <svg class="h-4 w-4 transform transition-transform group-open:rotate-180" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                </svg>
              </summary>
              <div class="mt-3 max-h-40 overflow-y-auto pr-2 custom-scrollbar">
                <p class="whitespace-pre-wrap text-xs text-gray-500 leading-relaxed">{{ imageImportPreview.ocrText }}</p>
              </div>
            </details>
          </div>

          <!-- 题目列表侧 -->
          <div class="space-y-5">
            <div class="flex items-center justify-between">
              <p class="text-sm font-medium text-gray-700">勾选需要添加的题目</p>
              <span class="inline-flex items-center rounded-full bg-purple-50 px-2.5 py-0.5 text-xs font-medium text-purple-700">
                已识别 {{ imageImportPreview.questions.length }} 题
              </span>
            </div>

            <div v-if="imageImportPreview.questions.length === 0" class="flex flex-col items-center justify-center py-16 rounded-xl border border-dashed border-gray-200 bg-gray-50/50">
              <p class="text-sm text-gray-500">未识别到有效题目</p>
            </div>

            <div v-else class="space-y-4">
              <div
                v-for="(question, index) in imageImportPreview.questions"
                :key="`preview_${index}`"
                class="rounded-xl border border-gray-100 bg-white p-5 shadow-sm transition-colors hover:border-gray-200"
              >
                <div class="mb-5 flex items-center justify-between gap-4">
                  <label class="flex items-center gap-3 cursor-pointer">
                    <input v-model="question.selected" type="checkbox" class="h-4 w-4 rounded border-gray-300 text-purple-600 focus:ring-purple-500" />
                    <span class="text-sm font-medium text-gray-900">题目 {{ index + 1 }}</span>
                  </label>
                  <select
                    v-model="question.type"
                    @change="handleQuestionTypeChange(question)"
                    class="rounded-lg border-gray-200 py-1.5 pl-3 pr-8 text-sm focus:border-purple-500 focus:ring-purple-500"
                  >
                    <option value="multiple_choice">单选题</option>
                    <option value="multiple_answer">多选题</option>
                    <option value="fill_blank">填空题</option>
                    <option value="short_answer">简答题</option>
                  </select>
                </div>

                <div class="space-y-4 pl-7">
                  <div>
                    <textarea
                      v-model="question.content"
                      rows="2"
                      class="block w-full resize-none rounded-lg border border-gray-200 bg-gray-50/50 px-3 py-2.5 text-sm transition-colors focus:border-purple-500 focus:bg-white focus:outline-none focus:ring-1 focus:ring-purple-500"
                    ></textarea>
                  </div>

                  <div v-if="['multiple_choice', 'multiple_answer'].includes(question.type)" class="space-y-2 mt-2">
                    <div
                      v-for="(option, optionIndex) in question.options"
                      :key="`preview_option_${index}_${optionIndex}`"
                      class="flex items-center gap-2"
                    >
                      <input
                        v-if="question.type === 'multiple_choice'"
                        v-model="question.answer"
                        type="radio"
                        :name="`preview_question_${index}`"
                        :value="optionIndex"
                        class="h-3.5 w-3.5 border-gray-300 text-purple-600 focus:ring-purple-500"
                      />
                      <input
                        v-else
                        type="checkbox"
                        :checked="isOptionSelected(question, optionIndex)"
                        @change="toggleAnswerOption(question, optionIndex)"
                        class="h-3.5 w-3.5 rounded border-gray-300 text-purple-600 focus:ring-purple-500"
                      />
                      <input
                        v-model="question.options[optionIndex]"
                        type="text"
                        class="flex-1 rounded-lg border-transparent hover:border-gray-200 px-3 py-1.5 text-sm focus:border-purple-500 focus:outline-none bg-transparent hover:bg-white focus:bg-white transition-colors"
                      />
                      <button type="button" class="text-gray-300 hover:text-red-500 p-1" @click="removeOption(question, optionIndex)">
                        <svg class="h-3.5 w-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
                      </button>
                    </div>
                  </div>

                  <div v-if="question.explanation">
                    <textarea
                      v-model="question.explanation"
                      rows="1"
                      class="block w-full resize-none rounded-lg border border-gray-200 bg-gray-50/50 px-3 py-2 text-sm text-gray-500"
                      placeholder="解析"
                    ></textarea>
                  </div>
                </div>
              </div>
            </div>
          </div>
        </div>

        <div class="flex items-center justify-end gap-3 border-t border-gray-100 px-8 py-4 bg-gray-50/30 shrink-0">
          <button
            type="button"
            @click="closeImageImportModal"
            class="rounded-lg px-5 py-2 text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors"
          >
            取消
          </button>
          <button
            type="button"
            @click="confirmImageImport"
            class="rounded-lg bg-blue-600 px-6 py-2 text-sm font-medium text-white shadow-sm hover:bg-blue-700 transition-colors"
          >
            确认添加
          </button>
        </div>
      </div>
    </div>

    <!-- AI生成评估模态框 -->
    <div v-if="showAiGenerationModal" class="fixed inset-0 z-[60] flex items-center justify-center bg-black/40 backdrop-blur-sm">
      <div class="bg-white rounded-2xl p-8 w-full max-w-lg shadow-2xl">
        <div class="flex items-center justify-between mb-6">
          <h3 class="text-xl font-semibold text-gray-900 flex items-center gap-2">
            <div class="flex h-8 w-8 items-center justify-center rounded-lg bg-purple-100 text-purple-600">
              <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path>
              </svg>
            </div>
            AI生成评估
          </h3>
          <button v-if="!isGenerating" @click="showAiGenerationModal = false" class="text-gray-400 hover:text-gray-600 p-1 rounded-full hover:bg-gray-100">
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" /></svg>
          </button>
        </div>
        
        <div v-if="isGenerating" class="py-10 text-center">
          <div class="relative mx-auto mb-6 h-16 w-16">
            <div class="absolute inset-0 rounded-full border-4 border-purple-100"></div>
            <div class="absolute inset-0 animate-spin rounded-full border-4 border-purple-600 border-t-transparent"></div>
          </div>
          <p class="text-base font-medium text-gray-800 mb-2">{{ statusMessage }}</p>
          <div class="mx-auto mt-6 w-64 overflow-hidden rounded-full bg-gray-100 h-1.5">
            <div class="bg-purple-600 h-full rounded-full progress-bar transition-all duration-300 ease-out"></div>
          </div>
          <p class="mt-4 text-xs text-gray-500">生成高质量评估内容可能需要 5-10 分钟，生成完成后会自动回填到表单</p>
        </div>
        
        <form v-else @submit.prevent="generateAssessmentWithAI" class="space-y-5">
          <div v-if="selectedChapter" class="rounded-xl border border-purple-100 bg-purple-50/50 px-4 py-3 text-sm text-purple-800 flex items-start gap-3">
            <svg class="h-5 w-5 text-purple-500 shrink-0 mt-0.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1 11-18 0 9 9 0 0118 0z"></path></svg>
            <div>
              <span class="font-medium">已选章节：{{ selectedChapter.title }}</span>
              <p class="mt-0.5 text-purple-600/80 text-xs">
                {{ selectedChapter.start_page ? '将优先参考该章节课件内容' : '将按章节标题与摘要生成' }}
              </p>
            </div>
          </div>

          <div class="grid grid-cols-2 gap-4">
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">评估类型</label>
              <select 
                v-model="aiGenerationParams.assessment_type" 
                class="block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
              >
                <option value="quiz">测验</option>
                <option value="exam">考试</option>
                <option value="homework">作业</option>
              </select>
            </div>
            
            <div>
              <label class="mb-1.5 block text-sm font-medium text-gray-700">难度</label>
              <select 
                v-model="aiGenerationParams.difficulty" 
                class="block w-full rounded-lg border border-gray-200 px-3 py-2 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
              >
                <option value="easy">简单</option>
                <option value="medium">中等</option>
                <option value="hard">困难</option>
              </select>
            </div>
          </div>
          
          <div>
            <label class="mb-1.5 block text-sm font-medium text-gray-700">额外要求或提示 <span class="text-gray-400 font-normal">(可选)</span></label>
            <textarea 
              v-model="aiGenerationParams.extra_info" 
              rows="3"
              class="block w-full resize-none rounded-lg border border-gray-200 px-3 py-2.5 text-sm transition-colors focus:border-purple-500 focus:outline-none focus:ring-1 focus:ring-purple-500"
              placeholder="例如：侧重于某个知识点、特定题型等"
            ></textarea>
          </div>
          
          <div class="mt-8 flex items-center justify-end gap-3 pt-2">
            <button 
              type="button"
              @click="showAiGenerationModal = false"
              class="rounded-lg px-5 py-2.5 text-sm font-medium text-gray-600 hover:bg-gray-100 transition-colors"
            >
              取消
            </button>
            <button 
              type="submit"
              class="rounded-lg bg-purple-600 px-6 py-2.5 text-sm font-medium text-white shadow-sm hover:bg-purple-700 focus:outline-none focus:ring-2 focus:ring-purple-500 focus:ring-offset-2 transition-colors"
            >
              开始生成
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref, watch, onMounted, onBeforeUnmount } from 'vue';
import { courseAPI, assessmentAPI } from '@/api';
import notificationService from '@/services/notificationService';

const props = defineProps({
  assessment: {
    type: Object,
    required: true
  }
});

const emit = defineEmits(['save', 'cancel']);

// 表单数据
const form = ref({
  title: props.assessment.title || '',
  description: props.assessment.description || '',
  course_id: props.assessment.course_id || '',
  total_score: props.assessment.total_score || 100,
  duration: props.assessment.duration || null,
  start_date: props.assessment.start_date || null,
  due_date: props.assessment.due_date || null,
  max_attempts: props.assessment.max_attempts || null,
  is_active: props.assessment.is_active || false,
  questions: props.assessment.questions || []
});
const showAdvancedSettings = ref(Boolean(
  props.assessment.duration ||
  props.assessment.start_date ||
  props.assessment.due_date ||
  props.assessment.max_attempts ||
  props.assessment.is_active
));

// 课程列表
const courses = ref([]);
const loading = ref(false);
const chapters = ref([]);
const chaptersLoading = ref(false);
const selectedChapterId = ref('');
const wordFileInput = ref(null);
const imageFileInput = ref(null);
const isImportingWord = ref(false);
const isImportingImage = ref(false);
const showImageImportModal = ref(false);
const imageImportPreview = reactive({
  fileName: '',
  previewUrl: '',
  parseMode: '',
  parseMessage: '',
  ocrText: '',
  ignoredTexts: [],
  questions: []
});
const selectedChapter = computed(() =>
  chapters.value.find(chapter => String(chapter.id) === String(selectedChapterId.value || '')) || null
);

// 获取课程列表
const fetchCourses = async () => {
  loading.value = true;
  try {
    const response = await courseAPI.getMyCourses();
    courses.value = response.courses || [];
  } catch (error) {
    console.error('获取课程列表失败:', error);
  } finally {
    loading.value = false;
  }
};

// 添加题目
const createQuestionDraft = (overrides = {}) => ({
  type: 'multiple_choice',
  content: '',
  options: ['', ''],
  answer: 0,
  answers: [false, false],
  score: 10,
  reference_answer: '',
  explanation: '',
  ...overrides
});

const normalizeImportedQuestion = (question = {}) => {
  const questionType = question.type || 'short_answer';
  const explanation = question.explanation || question.analysis || '';

  if (questionType === 'multiple_choice') {
    const options = Array.isArray(question.options) && question.options.length > 0
      ? question.options
      : ['', ''];

    return createQuestionDraft({
      type: 'multiple_choice',
      content: question.content || '',
      options,
      answer: typeof question.answer === 'number' ? question.answer : null,
      answers: Array(options.length).fill(false),
      score: question.score || 10,
      explanation,
      reference_answer: ''
    });
  }

  if (questionType === 'multiple_answer') {
    const options = Array.isArray(question.options) && question.options.length > 0
      ? question.options
      : ['', ''];

    return createQuestionDraft({
      type: 'multiple_answer',
      content: question.content || '',
      options,
      answer: '',
      answers: Array.isArray(question.answers) && question.answers.length === options.length
        ? question.answers
        : Array(options.length).fill(false),
      score: question.score || 10,
      explanation,
      reference_answer: ''
    });
  }

  if (questionType === 'fill_blank') {
    const blankCount = Number(question.blank_count) || 1;
    return createQuestionDraft({
      type: 'fill_blank',
      content: question.content || '',
      options: ['', ''],
      answer: blankCount > 1 ? Array(blankCount).fill('') : '',
      answers: [],
      score: question.score || 10,
      explanation,
      reference_answer: ''
    });
  }

  return createQuestionDraft({
    type: 'short_answer',
    content: question.content || '',
    options: ['', ''],
    answer: '',
    answers: [],
    score: question.score || 10,
    explanation,
    reference_answer: question.reference_answer || ''
  });
};

const createImagePreviewQuestion = (question = {}) => ({
  ...normalizeImportedQuestion(question),
  selected: question.selected !== false
});

const addQuestion = () => {
  form.value.questions.push(createQuestionDraft());
};

const resetImageImportPreview = () => {
  if (imageImportPreview.previewUrl) {
    URL.revokeObjectURL(imageImportPreview.previewUrl);
  }

  imageImportPreview.fileName = '';
  imageImportPreview.previewUrl = '';
  imageImportPreview.parseMode = '';
  imageImportPreview.parseMessage = '';
  imageImportPreview.ocrText = '';
  imageImportPreview.ignoredTexts = [];
  imageImportPreview.questions = [];
};

const closeImageImportModal = () => {
  showImageImportModal.value = false;
  resetImageImportPreview();
};

const triggerWordImport = () => {
  if (isImportingWord.value) {
    return;
  }

  if (wordFileInput.value) {
    wordFileInput.value.value = '';
    wordFileInput.value.click();
  }
};

const fetchChapters = async (courseId) => {
  if (!courseId) {
    chapters.value = [];
    return;
  }

  chaptersLoading.value = true;
  try {
    const response = await courseAPI.getCourseChapters(courseId);
    if (response && typeof response === 'object' && response.status === 'success' && Array.isArray(response.chapters)) {
      chapters.value = response.chapters.map((chapter, index) => ({
        ...chapter,
        id: String(chapter.id ?? index + 1),
        title: chapter.title || `第${index + 1}章`
      }));
    } else {
      chapters.value = [];
    }
  } catch (error) {
    console.error('获取章节失败:', error);
    chapters.value = [];
  } finally {
    chaptersLoading.value = false;
  }
};

const triggerImageImport = () => {
  if (isImportingImage.value) {
    return;
  }

  if (imageFileInput.value) {
    imageFileInput.value.value = '';
    imageFileInput.value.click();
  }
};

const handleWordImport = async (event) => {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }

  if (!file.name.toLowerCase().endsWith('.docx')) {
    notificationService.error('文件格式不支持', '当前仅支持导入 .docx 文件');
    event.target.value = '';
    return;
  }

  isImportingWord.value = true;

  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await assessmentAPI.importWordQuestion(formData);
    const importedQuestions = Array.isArray(response.questions) ? response.questions : [];

    if (importedQuestions.length === 0) {
      notificationService.warning('未识别到题目', '这个 Word 暂时没有解析出可导入的题目');
      return;
    }

    form.value.questions.push(...importedQuestions.map(normalizeImportedQuestion));

    const parseModeLabel = response.parse_mode === 'ai' ? 'AI 语义解析' : '规则解析';
    const parseMessage = response.parse_message ? `，${response.parse_message}` : '';
    notificationService.success('导入成功', `已从 ${file.name} 生成 ${importedQuestions.length} 道题目（${parseModeLabel}${parseMessage}）`);
  } catch (error) {
    console.error('导入 Word 题目失败:', error);
    const message =
      error?.response?.data?.error ||
      error?.response?.data?.message ||
      error?.message ||
      '请稍后重试';
    notificationService.error('导入失败', message);
  } finally {
    isImportingWord.value = false;
    event.target.value = '';
  }
};

const handleImageImport = async (event) => {
  const file = event.target.files?.[0];
  if (!file) {
    return;
  }

  if (!file.type.startsWith('image/')) {
    notificationService.error('文件格式不支持', '请上传常见图片格式');
    event.target.value = '';
    return;
  }

  isImportingImage.value = true;

  try {
    const formData = new FormData();
    formData.append('file', file);

    const response = await assessmentAPI.importImageQuestion(formData);
    const importedQuestions = Array.isArray(response.questions) ? response.questions : [];
    if (importedQuestions.length === 0) {
      notificationService.warning('未识别到题目', '这张图片暂时没有解析出可导入的题目');
      return;
    }

    resetImageImportPreview();
    imageImportPreview.fileName = file.name;
    imageImportPreview.previewUrl = URL.createObjectURL(file);
    imageImportPreview.parseMode = response.parse_mode || 'ai_ocr';
    imageImportPreview.parseMessage = response.parse_message || '';
    imageImportPreview.ocrText = response.ocr_text || '';
    imageImportPreview.ignoredTexts = Array.isArray(response.ignored_texts) ? response.ignored_texts : [];
    imageImportPreview.questions = importedQuestions.map(createImagePreviewQuestion);
    showImageImportModal.value = true;
  } catch (error) {
    console.error('导入图片题目失败:', error);
    const message =
      error?.response?.data?.error ||
      error?.response?.data?.message ||
      error?.message ||
      '请稍后重试';
    notificationService.error('图片识别失败', message);
  } finally {
    isImportingImage.value = false;
    event.target.value = '';
  }
};

const confirmImageImport = () => {
  const selectedQuestions = imageImportPreview.questions
    .filter(question => question.selected)
    .map(question => {
      const { selected, ...rest } = question;
      return normalizeImportedQuestion(rest);
    });

  if (selectedQuestions.length === 0) {
    notificationService.warning('未选择题目', '请至少勾选一道题再确认添加');
    return;
  }

  form.value.questions.push(...selectedQuestions);
  notificationService.success('添加成功', `已从图片中确认添加 ${selectedQuestions.length} 道题目`);
  closeImageImportModal();
};

// 删除题目
const removeQuestion = (index) => {
  form.value.questions.splice(index, 1);
};

// 添加选项
const addOption = (question) => {
  question.options.push('');
  
  // 如果是多选题，确保answers数组已初始化
  if (question.type === 'multiple_answer') {
    if (!question.answers) {
      question.answers = Array(question.options.length).fill(false);
    }
    // 为新选项添加一个默认为false的状态
    question.answers.push(false);
  }
};

// 填空题相关函数
const convertToMultipleAnswers = (question) => {
  // 将单一答案转换为数组形式
  const currentAnswer = question.answer;
  question.answer = [currentAnswer || ''];
};

const convertToSingleAnswer = (question) => {
  // 将多答案数组转换为单一答案
  if (Array.isArray(question.answer) && question.answer.length > 0) {
    question.answer = question.answer[0] || '';
  }
};

const addAnswer = (question) => {
  // 添加一个新的填空答案
  if (Array.isArray(question.answer)) {
    question.answer.push('');
  } else {
    question.answer = [question.answer || '', ''];
  }
};

const removeAnswer = (question, index) => {
  // 删除指定索引的填空答案
  if (Array.isArray(question.answer) && question.answer.length > 1) {
    question.answer.splice(index, 1);
  }
};

// 多选题相关函数
const isOptionSelected = (question, optionIndex) => {
  // 确保answers数组已初始化
  if (!question.answers) {
    question.answers = Array(question.options.length).fill(false);
  }
  
  // 如果answers数组长度不足，扩展它
  while (question.answers.length < question.options.length) {
    question.answers.push(false);
  }
  
  return question.answers[optionIndex];
};

const toggleAnswerOption = (question, optionIndex) => {
  // 确保answers数组已初始化
  if (!question.answers) {
    question.answers = Array(question.options.length).fill(false);
  }
  
  // 如果answers数组长度不足，扩展它
  while (question.answers.length < question.options.length) {
    question.answers.push(false);
  }
  
  // 切换选项状态
  question.answers[optionIndex] = !question.answers[optionIndex];
};

// 删除选项
const removeOption = (question, index) => {
  question.options.splice(index, 1);
  if (question.type === 'multiple_choice') {
    if (question.answer >= index) {
      question.answer = Math.max(0, question.answer - 1);
    }
  } else if (question.type === 'multiple_answer') {
    // 确保answers数组存在
    if (!question.answers) {
      question.answers = Array(question.options.length).fill(false);
    } else {
      // 移除对应的答案项
      question.answers.splice(index, 1);
    }
  }
};

// 处理题目保存
const handleSubmit = async () => {
  try {
    // 转换题目数据为sections格式
    const sections = [];
    
    // 按题目类型分组
    const groupedQuestions = {};
    
    form.value.questions.forEach(question => {
      if (!groupedQuestions[question.type]) {
        groupedQuestions[question.type] = [];
      }
      
      // 为填空题做特殊处理，确保类型正确
      let questionType = question.type;
      
      // 准备题目数据
      const questionData = {
        id: question.id || sections.length + groupedQuestions[question.type].length + 1,
        stem: question.content,
        score: question.score,
        type: questionType, // 保持原始类型
        explanation: question.explanation || '',
      };
      
      // 根据题目类型设置特定属性
      if (question.type === 'multiple_choice' || question.type === 'multiple_answer') {
        questionData.options = question.options;
        
        if (question.type === 'multiple_choice') {
          questionData.answer = question.answer;
        } else {
          // 多选题答案
          questionData.answer = question.answers
            .map((isSelected, index) => isSelected ? index : null)
            .filter(index => index !== null);
        }
      } else if (question.type === 'fill_blank' || question.type === 'fill_in_blank') {
        // 确保填空题答案格式正确
        if (Array.isArray(question.answer) && question.answer.length > 0) {
          questionData.answer = question.answer.map(item => item || '');
        } else if (typeof question.answer === 'string') {
          // 如果是单个空白，确保不是空字符串
          questionData.answer = question.answer || '';
        } else {
          // 默认值
          questionData.answer = '';
        }
        
        // 如果是填空题，也设置section_type属性确保兼容性
        questionData.section_type = 'fill_blank';
      } else if (question.type === 'true_false') {
        questionData.answer = question.answer;
      } else if (question.type === 'short_answer') {
        questionData.reference_answer = question.reference_answer || '';
      }
      
      groupedQuestions[question.type].push(questionData);
    });
    
    // 构建sections
    Object.entries(groupedQuestions).forEach(([type, questions]) => {
      if (questions.length > 0) {
        // 为填空题类型做特殊处理，确保兼容性
        let sectionType = type;
        if (type === 'fill_blank') {
          sectionType = 'fill_in_blank'; // 使用后端期望的类型
        }
        
        sections.push({
          type: sectionType,
          description: getSectionDescription(type),
          score_per_question: getAverageScore(questions),
          questions: questions
        });
      }
    });
    
    // 准备提交数据
    const assessmentData = {
      ...form.value,
      sections: sections
    };
    
    // 如果正在编辑现有评估
    if (props.assessment.id) {
      assessmentData.id = props.assessment.id;
    }
    
    // 发送保存事件
    emit('save', assessmentData);
    
  } catch (error) {
    console.error('准备评估数据失败:', error);
    alert('保存失败，请检查表单数据');
  }
};

// 获取分区描述
const getSectionDescription = (type) => {
  switch (type) {
    case 'multiple_choice': return '选择题：请在每小题给出的选项中选出一个正确答案。';
    case 'multiple_answer': return '多选题：请在每小题给出的选项中选出所有正确答案。';
    case 'fill_blank':
    case 'fill_in_blank': return '填空题：请在横线上填写正确的内容。';
    case 'true_false': return '判断题：请判断以下说法是否正确。';
    case 'short_answer': return '简答题：请简要回答以下问题。';
    default: return `${type}题`;
  }
};

// 计算平均分值
const getAverageScore = (questions) => {
  if (!questions || questions.length === 0) return 10;
  const totalScore = questions.reduce((sum, q) => sum + (q.score || 0), 0);
  return Math.round(totalScore / questions.length);
};

// 在组件挂载时获取课程列表
onMounted(async () => {
  await fetchCourses();
  if (form.value.course_id) {
    await fetchChapters(Number(form.value.course_id));
  }
});

onBeforeUnmount(() => {
  resetImageImportPreview();
});

watch(
  () => form.value.course_id,
  async (newCourseId, oldCourseId) => {
    if (String(newCourseId || '') === String(oldCourseId || '')) {
      return;
    }

    selectedChapterId.value = '';
    chapters.value = [];

    if (!newCourseId) {
      return;
    }

    await fetchChapters(Number(newCourseId));
  }
);

// AI生成评估相关逻辑
const showAiGenerationModal = ref(false);
const isGenerating = ref(false);
const aiGenerationParams = reactive({
  assessment_type: 'quiz',
  difficulty: 'medium',
  extra_info: ''
});
const statusMessage = ref('初始化中...');
const AI_ASSESSMENT_POLLING_INTERVAL_MS = 2000;
const AI_ASSESSMENT_ESTIMATED_TOTAL_SECONDS = 480;
const AI_ASSESSMENT_MAX_WAIT_SECONDS = 720;

// 辅助函数：处理和标准化评估数据
const processAssessmentData = (data) => {
  // 检查和提取评估数据，处理不同的数据结构
  let assessmentData = null;
  
  // 情况1: data本身就是评估数据
  if (data && data.title && (data.questions || data.sections)) {
    assessmentData = data;
  } 
  // 情况2: data.assessment包含评估数据
  else if (data && data.assessment) {
    assessmentData = data.assessment;
  }
  // 情况3: data可能是一个嵌套对象
  else if (data && typeof data === 'object') {
    // 尝试查找含有评估数据的对象
    for (const key in data) {
      if (data[key] && 
          (data[key].title || data[key].questions || data[key].sections) &&
          typeof data[key] === 'object') {
        assessmentData = data[key];
        break;
      }
    }
  }
  
  if (assessmentData) {
    console.log('成功提取评估数据:', assessmentData);
  } else {
    console.error('无法从响应中提取评估数据:', data);
  }
  
  return assessmentData;
};

const generateAssessmentWithAI = async () => {
  // 验证是否选择了课程
  if (!form.value.course_id) {
    showAiGenerationModal.value = false;
    alert('请先选择课程，AI需要课程信息来生成相关评估内容');
    return;
  }
  
  isGenerating.value = true;
  statusMessage.value = '正在初始化生成请求...';
  
  try {
    console.log('开始发送生成请求...');
    // 获取选中课程的信息
    const selectedCourse = courses.value.find(course => course.id == form.value.course_id) || {};
    
    // 准备请求数据
    const requestData = {
      course_name: selectedCourse.name || form.value.title || '',
      course_description: selectedCourse.description || form.value.description || '',
      assessment_type: aiGenerationParams.assessment_type,
      difficulty: aiGenerationParams.difficulty,
      extra_info: aiGenerationParams.extra_info,
      course_id: form.value.course_id,
      chapter_id: selectedChapterId.value || undefined,
      chapter_title: selectedChapter.value?.title || ''
    };
    
    console.log('发送AI生成请求:', requestData);
    statusMessage.value = '评估生成中...较复杂的内容可能需要 5-10 分钟，请保持页面开启';
    
    // 发送生成请求，获取请求ID
    const response = await assessmentAPI.generateAssessmentWithAI(requestData);
    console.log('收到AI生成响应:', response);
    
    // 检查响应中是否包含请求ID
    if (!response) {
      console.error('无响应对象');
      throw new Error('服务器未返回响应');
    }
    
    // 调试: 打印完整响应对象
    console.log('响应对象完整内容:', response);
    console.log('响应数据类型:', typeof response.data);
    
    // 检查 request_id 是否存在
    if (response.data && response.data.request_id) {
      const requestId = response.data.request_id;
      console.log('成功获取请求ID:', requestId);
      statusMessage.value = '正在获取生成结果...';
      
      // 设置轮询参数
      const pollingInterval = AI_ASSESSMENT_POLLING_INTERVAL_MS; // 2秒查询一次，减少生成完成后的等待感
      let assessmentData = null;
      let successfulResponses = 0; // 跟踪成功响应的次数
      let directFetchAttempted = false; // 是否已尝试直接获取文件
      let startTime = Date.now(); // 记录开始时间
      let progressPercentage = 0; // 进度百分比
      let attemptCount = 0; // 尝试次数计数
      
      // 动态更新进度条
      const updateProgressBar = (percentage) => {
        const progressBar = document.querySelector('.progress-bar');
        if (progressBar) {
          progressBar.style.width = `${percentage}%`;
          progressBar.style.animation = 'none'; // 停止动画，使用实际进度
        }
      };
      
      // 持续轮询直到获取结果或出错
      while (!assessmentData) {
        attemptCount++;
        
        try {
          // 等待一段时间后查询
          await new Promise(resolve => setTimeout(resolve, pollingInterval));
          
          const statusResponse = await assessmentAPI.getAIGenerationStatus(requestId);
          console.log(`查询状态 ${attemptCount}:`, statusResponse);
          
          // 安全检查: 确保statusResponse存在
          if (!statusResponse) {
            console.error(`查询状态响应为空:`, statusResponse);
            continue; // 继续尝试
          }
          
          // 处理不同的响应数据结构
          const responseData = statusResponse.data || statusResponse;
          
          console.log(`处理后的响应数据:`, responseData);
          
          // 计算经过的时间和估计进度
          const elapsedTime = (Date.now() - startTime) / 1000; // 经过的秒数
          const estimatedTotalTime = AI_ASSESSMENT_ESTIMATED_TOTAL_SECONDS; // 估计总时间（秒）
          
          // 根据后端返回的状态更新进度
          if (typeof responseData.progress_percent === 'number') {
            progressPercentage = Math.max(0, Math.min(95, responseData.progress_percent));
          } else if (responseData.progress && typeof responseData.progress === 'string') {
            // 尝试从进度消息中提取百分比
            const percentMatch = responseData.progress.match(/(\d+)%/);
            if (percentMatch && percentMatch[1]) {
              progressPercentage = parseInt(percentMatch[1]);
            } else if (responseData.progress.includes('解析')) {
              progressPercentage = 80;
            } else if (responseData.progress.includes('生成中')) {
              // 根据已经过时间估算进度
              progressPercentage = Math.min(70, Math.round((elapsedTime / estimatedTotalTime) * 100));
            }
          } else {
            // 如果没有明确的进度信息，根据时间和尝试次数估算
            progressPercentage = Math.min(90, Math.round((elapsedTime / estimatedTotalTime) * 100));
          }
          
          // 更新进度条
          updateProgressBar(progressPercentage);
          
          // 检查状态
          if (responseData.status === 'success' && responseData.assessment) {
            // 成功获取评估数据
            updateProgressBar(100);
            statusMessage.value = '评估生成完成！';
            assessmentData = processAssessmentData(responseData);
            if (assessmentData) break;
          } else if (responseData.status === 'error') {
            // 生成出错
            console.error('生成过程报错:', responseData.error || responseData.message);
            throw new Error(responseData.error || responseData.message || '生成失败');
          } else if (responseData.status === 'processing') {
            // 继续等待，更新进度信息
            console.log('生成仍在处理中:', responseData.progress || '无进度信息');
            if (responseData.progress) {
              statusMessage.value = responseData.progress;
            }
          } else if (responseData.status === 'success' || responseData.message?.includes('已生成完成')) {
            // 后端返回成功状态但没有直接返回评估数据
            updateProgressBar(95);
            statusMessage.value = '评估已生成，正在获取数据...';
            successfulResponses++;
            
            // 如果收到成功响应但没有评估数据，尝试直接获取文件
            if (!directFetchAttempted || successfulResponses >= 2) {
              directFetchAttempted = true;
              console.log("检测到评估已完成，尝试直接获取评估文件内容...");
              
              try {
                const directResponse = await fetch(`/api/assessments/ai-file/${requestId}`, {
                  method: 'GET',
                  headers: { 'Content-Type': 'application/json' }
                });
                
                if (directResponse.ok) {
                  const fileData = await directResponse.json();
                  if (fileData && (fileData.assessment || fileData.data?.assessment)) {
                    console.log('通过直接访问文件获取评估数据:', fileData);
                    updateProgressBar(100);
                    statusMessage.value = '评估生成完成！';
                    assessmentData = processAssessmentData(fileData);
                    if (assessmentData) break;
                  }
                }
              } catch (fileError) {
                console.warn('直接获取文件失败，继续轮询:', fileError);
                // 继续轮询，不中断流程
              }
            }
          } else {
            // 未识别的状态
            console.warn(`未识别的状态响应:`, responseData);
            
            // 如果轮询次数较多，尝试直接获取文件
            if (attemptCount >= 4 && !directFetchAttempted) {
              directFetchAttempted = true;
              console.log("轮询多次后尝试直接获取评估文件...");
              
              try {
                const directResponse = await fetch(`/api/assessments/ai-file/${requestId}`, {
                  method: 'GET',
                  headers: { 'Content-Type': 'application/json' }
                });
                
                if (directResponse.ok) {
                  const fileData = await directResponse.json();
                  if (fileData && (fileData.assessment || fileData.data?.assessment)) {
                    console.log('通过直接访问文件获取评估数据:', fileData);
                    updateProgressBar(100);
                    statusMessage.value = '评估生成完成！';
                    assessmentData = processAssessmentData(fileData);
                    if (assessmentData) break;
                  }
                }
              } catch (fileError) {
                console.warn('直接获取文件失败，继续轮询:', fileError);
              }
            }
          }
          
          // 安全机制：如果轮询时间超过4分钟，主动尝试直接获取文件并结束
          if (elapsedTime > AI_ASSESSMENT_MAX_WAIT_SECONDS && !assessmentData) {
            console.log("轮询超时，最后尝试直接获取文件...");
            try {
              const directResponse = await fetch(`/api/assessments/ai-file/${requestId}`, {
                method: 'GET',
                headers: { 'Content-Type': 'application/json' }
              });
              
              if (directResponse.ok) {
                const fileData = await directResponse.json();
                if (fileData && (fileData.assessment || fileData.data?.assessment)) {
                  updateProgressBar(100);
                  statusMessage.value = '评估生成完成！';
                  assessmentData = processAssessmentData(fileData);
                }
              }
            } catch (error) {
              console.error("最终尝试获取文件失败:", error);
            }
            
            // 如果仍然没有获取到数据，抛出超时错误
            if (!assessmentData) {
              throw new Error('等待评估生成结果超时。后台可能仍在继续处理，请稍后在评估列表中查看或重新打开编辑器确认结果。');
            }
            break;
          }
        } catch (err) {
          console.error('查询状态失败:', err);
          
          // 如果错误不是由我们主动抛出的超时错误，则尝试继续
          if (!err.message.includes('超时')) {
            console.log(`将在${pollingInterval/1000}秒后重试...`);
            continue;
          } else {
            // 超时错误直接抛出
            throw err;
          }
        }
      }
      
      // 如果成功获取到评估数据
      if (assessmentData) {
        // 应用到表单
        form.value.title = assessmentData.title || form.value.title;
        form.value.description = assessmentData.description || form.value.description;
        
        // 处理题目数据
        let questions = [];
        
        try {
          console.log('处理评估题目数据:', assessmentData);
          
          // 处理sections格式
          if (assessmentData.sections && assessmentData.sections.length > 0) {
            console.log('使用sections格式处理题目');
            assessmentData.sections.forEach(section => {
              if (section.questions && section.questions.length > 0) {
                section.questions.forEach(q => {
                  // 处理选项 - 如果选项是字符串数组
                  const options = q.options || [];
                  
                  // 将AI生成的题型映射到前端支持的题型
                  let mappedType = q.type || section.type || 'multiple_choice';
                  let mappedAnswer = q.answer || '';
                  
                  // 题型映射
                  if (mappedType === 'multiple_select') {
                    mappedType = 'multiple_answer'; // 多选题映射
                  } else if (mappedType === 'essay') {
                    mappedType = 'short_answer'; // 论述题映射为简答题
                  } else if (mappedType === 'fill_in_blank') {
                    mappedType = 'fill_blank'; // 填空题映射
                  }
                  
                  // 答案处理
                  if (mappedType === 'multiple_choice') {
                    // 单选题答案处理
                    if (typeof mappedAnswer === 'string' && /^[A-Z]$/.test(mappedAnswer)) {
                      // 如果答案是字母A-Z，转换为索引
                      mappedAnswer = mappedAnswer.charCodeAt(0) - 65; // A=0, B=1, ...
                    }
                  } else if (mappedType === 'multiple_answer') {
                    // 多选题答案处理
                    let answers = [];
                    if (Array.isArray(mappedAnswer)) {
                      answers = mappedAnswer.map(ans => {
                        if (typeof ans === 'string' && /^[A-Z]$/.test(ans)) {
                          return ans.charCodeAt(0) - 65; // A=0, B=1, ...
                        }
                        return ans;
                      });
                    }
                    mappedAnswer = answers;
                  }
                  
                  // 标准化问题对象
                  questions.push({
                    id: questions.length + 1,
                    type: mappedType,
                    content: q.stem || q.question || '',
                    score: parseFloat(q.score || section.score_per_question || 5),
                    options: options,
                    answer: mappedType === 'multiple_answer' ? 0 : (mappedType === 'short_answer' ? '' : mappedAnswer), // 单选题用answer
                    answers: mappedType === 'multiple_answer' ? mappedAnswer : undefined, // 多选题用answers
                    explanation: q.explanation || '',
                    reference_answer: mappedType === 'short_answer' ? (q.reference_answer || q.answer || '') : '' // 保存参考答案
                  });
                });
              }
            });
          } 
          // 处理直接的questions格式
          else if (assessmentData.questions) {
            console.log('使用questions格式处理题目');
            assessmentData.questions.forEach((q, index) => {
              // 将AI生成的题型映射到前端支持的题型
              let mappedType = q.type || 'multiple_choice';
              let mappedAnswer = q.answer || '';
              
              // 题型映射
              if (mappedType === 'multiple_select') {
                mappedType = 'multiple_answer'; // 多选题映射
              } else if (mappedType === 'essay') {
                mappedType = 'short_answer'; // 论述题映射为简答题
              } else if (mappedType === 'fill_in_blank') {
                mappedType = 'fill_blank'; // 填空题映射
              }
              
              // 答案处理
              if (mappedType === 'multiple_choice') {
                // 单选题答案处理
                if (typeof mappedAnswer === 'string' && /^[A-Z]$/.test(mappedAnswer)) {
                  // 如果答案是字母A-Z，转换为索引
                  mappedAnswer = mappedAnswer.charCodeAt(0) - 65; // A=0, B=1, ...
                }
              } else if (mappedType === 'multiple_answer') {
                // 多选题答案处理
                let answers = [];
                if (Array.isArray(mappedAnswer)) {
                  answers = mappedAnswer.map(ans => {
                    if (typeof ans === 'string' && /^[A-Z]$/.test(ans)) {
                      return ans.charCodeAt(0) - 65; // A=0, B=1, ...
                    }
                    return ans;
                  });
                }
                mappedAnswer = answers;
              }
              
              questions.push({
                id: index + 1,
                type: mappedType,
                content: q.stem || q.question || '',
                score: parseFloat(q.score || 5),
                options: q.options || [],
                answer: mappedType === 'multiple_answer' ? 0 : mappedAnswer, // 单选题用answer
                answers: mappedType === 'multiple_answer' ? mappedAnswer : undefined, // 多选题用answers
                explanation: q.explanation || '',
                reference_answer: q.reference_answer || q.answer || '' // 保存参考答案
              });
            });
          }
          // 尝试处理其他可能的格式
          else if (Array.isArray(assessmentData)) {
            console.log('处理数组格式的题目');
            assessmentData.forEach((q, index) => {
              // 将AI生成的题型映射到前端支持的题型
              let mappedType = q.type || 'multiple_choice';
              let mappedAnswer = q.answer || '';
              
              // 题型映射
              if (mappedType === 'multiple_select') {
                mappedType = 'multiple_answer'; // 多选题映射
              } else if (mappedType === 'essay') {
                mappedType = 'short_answer'; // 论述题映射为简答题
              } else if (mappedType === 'fill_in_blank') {
                mappedType = 'fill_blank'; // 填空题映射
              }
              
              // 答案处理
              if (mappedType === 'multiple_choice') {
                // 单选题答案处理
                if (typeof mappedAnswer === 'string' && /^[A-Z]$/.test(mappedAnswer)) {
                  // 如果答案是字母A-Z，转换为索引
                  mappedAnswer = mappedAnswer.charCodeAt(0) - 65; // A=0, B=1, ...
                }
              } else if (mappedType === 'multiple_answer') {
                // 多选题答案处理
                let answers = [];
                if (Array.isArray(mappedAnswer)) {
                  answers = mappedAnswer.map(ans => {
                    if (typeof ans === 'string' && /^[A-Z]$/.test(ans)) {
                      return ans.charCodeAt(0) - 65; // A=0, B=1, ...
                    }
                    return ans;
                  });
                }
                mappedAnswer = answers;
              }
              
              questions.push({
                id: index + 1,
                type: mappedType,
                content: q.stem || q.question || '',
                score: parseFloat(q.score || 5),
                options: q.options || [],
                answer: mappedType === 'multiple_answer' ? 0 : mappedAnswer, // 单选题用answer
                answers: mappedType === 'multiple_answer' ? mappedAnswer : undefined, // 多选题用answers
                explanation: q.explanation || '',
                reference_answer: q.reference_answer || q.answer || '' // 保存参考答案
              });
            });
          }
          
          // 设置题目
          if (questions.length > 0) {
            console.log(`成功处理 ${questions.length} 道题目`);
            form.value.questions = questions;
          } else {
            console.warn('没有找到有效的题目数据');
            if (assessmentData.content) {
              // 尝试解析content字段作为原始数据
              try {
                const contentData = typeof assessmentData.content === 'string' 
                  ? JSON.parse(assessmentData.content)
                  : assessmentData.content;
                
                if (contentData && (contentData.questions || contentData.sections)) {
                  console.log('从content字段中提取评估数据，重新处理');
                  const reprocessedData = processAssessmentData(contentData);
                  if (reprocessedData) {
                    // 递归调用自身处理新提取的数据
                    return generateAssessmentWithAI();
                  }
                }
              } catch (parseError) {
                console.error('解析content字段失败:', parseError);
              }
            }
          }
        } catch (processError) {
          console.error('处理评估数据时出错:', processError);
        }
        
        // 关闭模态框并显示成功消息
        showAiGenerationModal.value = false;
        isGenerating.value = false;
        alert('评估内容生成成功！');
        return;
      } else {
        throw new Error('超时或未能获取有效的评估数据');
      }
    } else {
      console.error('响应格式错误，缺少request_id:', response.data);
      throw new Error('服务器响应格式错误，缺少必要的请求ID');
    }
  } catch (error) {
    console.error('生成评估失败:', error);
    alert('生成评估失败: ' + (error.message || '未知错误'));
  } finally {
    isGenerating.value = false;
    showAiGenerationModal.value = false;
  }
};

// 监听题目类型变化，确保相应字段初始化
const handleQuestionTypeChange = (question) => {
  if (['multiple_choice', 'multiple_answer'].includes(question.type)) {
    if (!Array.isArray(question.options) || question.options.length < 2) {
      question.options = ['', ''];
    }
  }

  if (question.type === 'multiple_choice') {
    if (typeof question.answer !== 'number' || question.answer < 0) {
      question.answer = null;
    }
    question.answers = Array(question.options.length).fill(false);
  }

  if (question.type === 'multiple_answer') {
    if (!Array.isArray(question.answers) || question.answers.length !== question.options.length) {
      question.answers = Array(question.options.length).fill(false);
    }
    question.answer = '';
  }

  if (question.type === 'fill_blank') {
    if (question.answer === undefined || question.answer === null || question.answer === '') {
      question.answer = '';
    }
    question.options = ['', ''];
    question.answers = [];
  }

  if (question.type === 'short_answer') {
    if (question.reference_answer === undefined) {
      question.reference_answer = typeof question.answer === 'string' ? question.answer : '';
    }
    question.answer = '';
    question.options = ['', ''];
    question.answers = [];
  }
};
</script>

<style>
.progress-bar {
  animation: progress-animation 3s infinite;
  width: 30%;
}

@keyframes progress-animation {
  0% { width: 5%; }
  50% { width: 70%; }
  100% { width: 5%; }
}
</style> 
