<template>
  <div>
    <div v-if="loading" class="flex justify-center items-center h-64">
      <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
    </div>

    <div v-else-if="showMaterialPreview" class="bg-white rounded-lg shadow-md overflow-hidden">
      <div class="flex h-[calc(100vh-9rem)] min-h-[720px]">
        <div class="min-w-0 flex-1">
          <MaterialPreview 
            :courseId="courseId" 
            :initialMaterialId="previewMaterialId"
            :hideBackButton="true"
            @close="showMaterialPreview = false"
          />
        </div>

        <aside class="hidden lg:flex w-[350px] shrink-0 border-l bg-white">
          <AIAssistant
            :courseId="courseId"
            minimal
            class="h-full flex-1"
          />
        </aside>
      </div>
    </div>

    <div v-else-if="loadError" class="rounded-lg border border-rose-200 bg-rose-50 px-6 py-10 text-center shadow-sm">
      <div class="mx-auto flex h-12 w-12 items-center justify-center rounded-full bg-white text-rose-500 shadow-sm">
        <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 20 20" fill="currentColor">
          <path fill-rule="evenodd" d="M18 10A8 8 0 114.293 4.293 8 8 0 0118 10zm-9-3a1 1 0 112 0v3a1 1 0 11-2 0V7zm0 6a1 1 0 112 0 1 1 0 01-2 0z" clip-rule="evenodd" />
        </svg>
      </div>
      <h2 class="mt-4 text-xl font-semibold text-rose-900">课程详情加载失败</h2>
      <p class="mt-2 text-sm leading-6 text-rose-800">{{ loadError }}</p>
      <p class="mt-1 text-xs text-rose-700">课程 ID：{{ courseId }}</p>
      <div class="mt-6 flex flex-wrap justify-center gap-3">
        <button
          @click="retryLoadCourseDetail"
          class="rounded-md bg-rose-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-rose-700"
        >
          重试加载
        </button>
        <button
          @click="goBackToDashboard"
          class="rounded-md border border-rose-200 bg-white px-4 py-2 text-sm font-medium text-rose-700 transition hover:bg-rose-100"
        >
          返回课程列表
        </button>
      </div>
    </div>

    <div v-else-if="course" class="bg-white rounded-lg shadow-md overflow-hidden">
      <!-- 课程头部信息 -->
      <div class="p-6 border-b">
        <div class="flex justify-between items-start">
          <div>
            <h1 class="text-2xl font-bold mb-2">{{ course.name }}</h1>
            <p class="text-gray-600 mb-4">{{ course.description }}</p>
            <div class="flex flex-wrap gap-2 mb-2">
              <span class="px-3 py-1 rounded-full text-sm bg-gray-100 text-gray-800">
                {{ course.category }}
              </span>
              <span :class="[
                'px-3 py-1 rounded-full text-sm', 
                difficultyClass(course.difficulty)
              ]">
                {{ difficultyText(course.difficulty) }}
              </span>
            </div>
            <p class="text-sm text-gray-500">
              教师: {{ course.teacher_name }}
            </p>
          </div>
        </div>
      </div>

      <!-- 选项卡导航 -->
      <div class="border-b">
        <nav class="flex">
          <button
            v-for="tab in tabs"
            :key="tab.id"
            @click="activeTab = tab.id"
            :class="[
              'px-6 py-3 text-center border-b-2 font-medium',
              activeTab === tab.id
                ? 'border-blue-500 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700 hover:border-gray-300'
            ]"
          >
            {{ tab.name }}
          </button>
        </nav>
      </div>

      <!-- 选项卡内容 -->
      <div class="tab-content">
        <!-- 章节内容 -->
        <div v-if="activeTab === 'chapters'" class="p-6">
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-lg font-semibold">章节内容</h3>
            <div class="flex space-x-2">
              <button
                v-if="canEdit && course.chapters && course.chapters.length > 0"
                @click="openMaterialChapterModal"
                class="px-4 py-2 bg-amber-500 text-white rounded-md flex items-center"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V9.414a2 2 0 00-.586-1.414l-4.414-4.414A2 2 0 008 3H4zm5 1.5V8a1 1 0 001 1h3.5L9 4.5z" />
                  <path d="M15 12a1 1 0 011 1v1h1a1 1 0 110 2h-1v1a1 1 0 11-2 0v-1h-1a1 1 0 110-2h1v-1a1 1 0 011-1z" />
                </svg>
                读取课件资源生成
              </button>
              <button 
                v-if="canEdit && course.chapters && course.chapters.length > 0" 
                @click="openEditChapterModal"
                class="px-4 py-2 bg-blue-600 text-white rounded-md flex items-center"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M13.586 3.586a2 2 0 112.828 2.828l-.793.793-2.828-2.828.793-.793zM11.379 5.793L3 14.172V17h2.828l8.38-8.379-2.83-2.828z" />
                </svg>
                修改章节
              </button>
              <button 
                v-if="canEdit && course.chapters && course.chapters.length > 0" 
                @click="generateChaptersWithAI"
                class="px-4 py-2 bg-green-600 text-white rounded-md flex items-center"
                :disabled="isGeneratingChapters"
              >
                <span v-if="isGeneratingChapters" class="mr-1">
                  <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </span>
                <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M10 3.5a1.5 1.5 0 013 0V4a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-.5a1.5 1.5 0 000 3h.5a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-.5a1.5 1.5 0 00-3 0v.5a1 1 0 01-1 1H6a1 1 0 01-1-1v-3a1 1 0 011-1h.5a1.5 1.5 0 000-3H6a1 1 0 01-1-1V6a1 1 0 011-1h3a1 1 0 001-1v-.5z" />
                </svg>
                {{ isGeneratingChapters ? '生成中...' : '使用AI重新生成' }}
              </button>
            </div>
          </div>

          <div v-if="course.chapters && course.chapters.length > 0" class="space-y-4">
            <details v-if="displayedCourseChapters.frontMatter.length > 0" class="overflow-hidden rounded-md border border-amber-200 bg-amber-50/60">
              <summary class="cursor-pointer px-4 py-3 text-left">
                <div class="flex items-center justify-between gap-4">
                  <div>
                    <p class="font-medium text-amber-900">第一章前置内容</p>
                    <p class="mt-1 text-sm text-amber-700">已折叠封面、序、前言等 {{ displayedCourseChapters.frontMatter.length }} 项内容</p>
                  </div>
                  <span class="text-sm text-amber-700">展开查看</span>
                </div>
              </summary>
              <div class="space-y-3 border-t border-amber-200 px-3 py-3">
                <div
                  v-for="item in displayedCourseChapters.frontMatter"
                  :key="`front-${item.originalIndex}`"
                  class="border rounded-md overflow-hidden cursor-pointer bg-white hover:bg-gray-50"
                  @click="goLearning(item.originalIndex, item.chapter.start_page)"
                >
                  <div class="flex justify-between items-center p-4 bg-amber-50/70">
                    <h4 class="font-medium">{{ item.chapter.title }}</h4>
                    <span class="text-sm text-gray-500">{{ item.chapter.duration }}分钟</span>
                  </div>
                  <div v-if="item.chapter.sections && item.chapter.sections.length > 0" class="divide-y">
                    <div v-for="(section, sectionIndex) in item.chapter.sections" :key="sectionIndex" class="p-4 pl-8 flex justify-between items-center">
                      <span>{{ section.title }}</span>
                      <span class="text-sm text-gray-500">{{ section.duration }}分钟</span>
                    </div>
                  </div>
                  <div v-else class="p-4 pl-8 text-gray-500 italic">
                    暂无小节内容
                  </div>
                </div>
              </div>
            </details>

            <template v-for="(group, groupIndex) in displayedCourseChapters.groups" :key="`group-${group.heading || 'default'}-${groupIndex}`">
              <div v-if="group.heading" class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                <div class="flex items-center justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold tracking-wide text-slate-500">分册 / 分部</p>
                    <h4 class="mt-1 text-lg font-semibold text-slate-900">{{ group.heading }}</h4>
                  </div>
                  <span class="text-sm text-slate-500">{{ group.items.length }} 章</span>
                </div>
              </div>

              <div
                v-for="item in group.items"
                :key="item.displayKey"
                class="border rounded-md overflow-hidden cursor-pointer hover:bg-gray-50"
                @click="goLearning(item.originalIndex, item.chapter.start_page)"
              >
                <div class="flex justify-between items-center p-4 bg-gray-50">
                  <h4 class="font-medium">{{ item.chapter.title }}</h4>
                  <span class="text-sm text-gray-500">{{ item.chapter.duration }}分钟</span>
                </div>
                <div v-if="item.chapter.sections && item.chapter.sections.length > 0" class="divide-y">
                  <div v-for="(section, sectionIndex) in item.chapter.sections" :key="sectionIndex" class="p-4 pl-8 flex justify-between items-center">
                    <span>{{ section.title }}</span>
                    <span class="text-sm text-gray-500">{{ section.duration }}分钟</span>
                  </div>
                </div>
                <div v-else class="p-4 pl-8 text-gray-500 italic">
                  暂无小节内容
                </div>
              </div>
            </template>
          </div>
          <div v-else class="text-center py-10">
            <p class="text-gray-500">暂无章节内容</p>
            <div class="flex justify-center mt-4 space-x-3">
              <button 
                v-if="canEdit" 
                @click="showAddChapterModal = true"
                class="px-4 py-2 bg-blue-600 text-white rounded-md flex items-center"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
                </svg>
                添加章节
              </button>
              <button
                v-if="canEdit"
                @click="openMaterialChapterModal"
                class="px-4 py-2 bg-amber-500 text-white rounded-md flex items-center"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h8a2 2 0 002-2V9.414a2 2 0 00-.586-1.414l-4.414-4.414A2 2 0 008 3H4zm5 1.5V8a1 1 0 001 1h3.5L9 4.5z" />
                  <path d="M15 12a1 1 0 011 1v1h1a1 1 0 110 2h-1v1a1 1 0 11-2 0v-1h-1a1 1 0 110-2h1v-1a1 1 0 011-1z" />
                </svg>
                读取课件资源生成
              </button>
              <button 
                v-if="canEdit" 
                @click="generateChaptersWithAI"
                class="px-4 py-2 bg-green-600 text-white rounded-md flex items-center"
                :disabled="isGeneratingChapters"
              >
                <span v-if="isGeneratingChapters" class="mr-1">
                  <svg class="animate-spin h-5 w-5" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                    <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                    <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                  </svg>
                </span>
                <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                  <path d="M10 3.5a1.5 1.5 0 013 0V4a1 1 0 001 1h3a1 1 0 011 1v3a1 1 0 01-1 1h-.5a1.5 1.5 0 000 3h.5a1 1 0 011 1v3a1 1 0 01-1 1h-3a1 1 0 01-1-1v-.5a1.5 1.5 0 00-3 0v.5a1 1 0 01-1 1H6a1 1 0 01-1-1v-3a1 1 0 011-1h.5a1.5 1.5 0 000-3H6a1 1 0 01-1-1V6a1 1 0 011-1h3a1 1 0 001-1v-.5z" />
                </svg>
                {{ isGeneratingChapters ? '生成中...' : '使用AI生成章节' }}
              </button>
            </div>
          </div>
        </div>

        <!-- 课件资源 -->
        <div v-else-if="activeTab === 'materials'" class="p-6">
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-lg font-semibold">课件资源</h3>
            <button 
              @click="openMaterialModal"
              class="px-4 py-2 bg-blue-600 text-white rounded-md"
            >
              上传课件
            </button>
          </div>

          <div v-if="materials.length > 0" class="space-y-4">
            <div v-for="material in materials" :key="material.id" class="flex items-center justify-between p-4 border rounded-md">
              <div class="flex items-center">
                <span class="mr-3" v-html="getMaterialIcon(material.material_type)"></span>
                <div>
                  <p class="font-medium">{{ material.title }}</p>
                  <p class="text-sm text-gray-500">{{ material.material_type }} · {{ material.size }}</p>
                  <!-- 知识库状态显示 -->
                  <div v-if="material.file_path" class="mt-1">
                    <span v-if="isSupportedForKnowledgeBase(material)" class="text-xs px-2 py-1 rounded-full bg-green-100 text-green-800">
                      支持知识库
                    </span>
                    <span v-else class="text-xs px-2 py-1 rounded-full bg-gray-100 text-gray-600">
                      不支持知识库
                    </span>
                  </div>
                </div>
              </div>
              <div class="flex flex-wrap items-center gap-3">
                <button @click="previewMaterial(material.id)" class="text-blue-600 hover:text-blue-800">预览</button>
                <button @click="downloadMaterial(material.id)" class="text-blue-600 hover:text-blue-800">下载</button>
                <div
                  v-if="isSupportedForKnowledgeBase(material)"
                  class="inline-flex items-center rounded-full bg-gray-100 p-1 text-xs"
                >
                  <button
                    type="button"
                    @click="knowledgePurposeSelection[material.id] = 'general'"
                    :class="[
                      'rounded-full px-3 py-1 transition',
                      knowledgePurposeSelection[material.id] === 'general'
                        ? 'bg-white text-blue-600 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    ]"
                  >
                    通用
                  </button>
                  <button
                    type="button"
                    @click="knowledgePurposeSelection[material.id] = 'lesson_plan'"
                    :class="[
                      'rounded-full px-3 py-1 transition',
                      knowledgePurposeSelection[material.id] === 'lesson_plan'
                        ? 'bg-white text-blue-600 shadow-sm'
                        : 'text-gray-500 hover:text-gray-700'
                    ]"
                  >
                    备课
                  </button>
                </div>
                <button 
                  v-if="isSupportedForKnowledgeBase(material)"
                  @click="addToKnowledgeBase(material)"
                  class="text-green-600 hover:text-green-800 disabled:opacity-50 disabled:cursor-not-allowed"
                  :disabled="isProcessingKnowledgeBase(material) || knowledgeBaseProcessing[material.id]"
                >
                  {{ getKnowledgeBaseButtonText(material) }}
                </button>
                <button @click="confirmDeleteMaterial(material)" class="text-red-600 hover:text-red-800">删除</button>
              </div>
            </div>
          </div>
          <div v-else class="text-center py-10">
            <p class="text-gray-500">暂无课件资源</p>
          </div>
        </div>

        <!-- 评估测验 -->
        <div v-else-if="activeTab === 'assessments'" class="p-6">
          <div class="max-w-7xl mx-auto">
            <div class="mb-6 flex justify-between items-center">
              <h3 class="text-lg font-semibold">评估测验</h3>
              <div v-if="canEdit">
                <button 
                  @click="createNewAssessment"
                  class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  创建评估
                </button>
              </div>
            </div>

            <div v-if="assessments.length > 0" class="space-y-4">
              <div 
                v-for="assessment in assessments" 
                :key="assessment.id" 
                class="bg-white p-6 rounded-lg shadow-md border border-gray-200"
              >
                <div class="flex justify-between items-start">
                  <div>
                    <h4 class="text-lg font-semibold">{{ assessment.title }}</h4>
                    <p class="text-sm text-gray-600">{{ assessment.description }}</p>
                    <div class="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-sm text-gray-500">
                      <span>总分: {{ assessment.total_score }}</span>
                      <span>题目数: {{ getTotalQuestions(assessment) }}</span>
                      <span>时间限制: {{ assessment.duration || '无限制' }}</span>
                      <span>截止日期: {{ formatDate(assessment.due_date) }}</span>
                      <span>尝试次数: {{ assessment.max_attempts || '无限制' }}</span>
                    </div>
                  </div>
                  
                  <div class="flex flex-col gap-2">
                    <span 
                      :class="getStatusClass(assessment)"
                      class="px-2 py-1 text-xs rounded-full"
                    >
                      {{ getStatusText(assessment) }}
                    </span>
                    
                    <div class="flex gap-2 mt-2">
                      <router-link 
                        :to="`/assessments/${assessment.id}`" 
                        class="text-blue-600 hover:text-blue-800"
                      >
                        查看
                      </router-link>
                      
                      <button 
                        v-if="canEdit"
                        @click="editAssessment(assessment)"
                        class="text-green-600 hover:text-green-800"
                      >
                        编辑
                      </button>
                      
                      <button 
                        v-if="canEdit"
                        @click="confirmDeleteAssessment(assessment)"
                        class="text-red-600 hover:text-red-800"
                      >
                        删除
                      </button>
                    </div>
                  </div>
                </div>
              </div>
            </div>
            <div v-else class="text-center py-10">
              <p class="text-gray-500">暂无评估测验</p>
              <div v-if="canEdit" class="mt-4">
                <button 
                  @click="createNewAssessment"
                  class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
                >
                  创建评估
                </button>
              </div>
            </div>
          </div>
        </div>

        <!-- 学生列表 -->
        <div v-else-if="activeTab === 'students'" class="p-6">
          <div class="flex justify-between items-center mb-6">
            <h3 class="text-lg font-semibold">学生列表</h3>
            <button 
              v-if="canEdit" 
              @click="openAddStudentsModal"
              class="px-4 py-2 bg-blue-600 text-white rounded-md"
            >
              添加学生
            </button>
          </div>

          <div v-if="loading" class="flex justify-center py-10">
            <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
          </div>

          <div v-else-if="students.length > 0">
            <div class="overflow-x-auto">
              <table class="min-w-full bg-white">
                <thead>
                  <tr>
                    <th class="py-2 px-4 border-b text-left">学号</th>
                    <th class="py-2 px-4 border-b text-left">姓名</th>
                    <th class="py-2 px-4 border-b text-left">邮箱</th>
                    <th class="py-2 px-4 border-b text-left">加入时间</th>
                    <th class="py-2 px-4 border-b text-left">操作</th>
                  </tr>
                </thead>
                <tbody>
                  <tr v-for="student in students" :key="student.id" class="hover:bg-gray-50">
                    <td class="py-2 px-4 border-b">{{ student.id }}</td>
                    <td class="py-2 px-4 border-b">{{ student.name }}</td>
                    <td class="py-2 px-4 border-b">{{ student.email }}</td>
                    <td class="py-2 px-4 border-b">{{ student.last_activity || '未记录' }}</td>
                    <td class="py-2 px-4 border-b">
                      <button 
                        v-if="canEdit"
                        @click="confirmRemoveStudent(student)"
                        class="text-red-600 hover:text-red-800"
                      >
                        移除
                      </button>
                    </td>
                  </tr>
                </tbody>
              </table>
            </div>
          </div>
          <div v-else class="text-center py-10">
            <p class="text-gray-500">暂无学生</p>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加课件模态框 -->
    <div v-if="showAddMaterialModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-lg">
        <h3 class="text-xl font-bold mb-4">上传课件资源</h3>
        <form @submit.prevent="uploadMaterial">
          <div class="mb-4">
            <label class="block text-gray-700 text-sm font-bold mb-2">课件标题</label>
            <input v-model="materialTitle" type="text" class="w-full px-3 py-2 border rounded-md" placeholder="输入课件标题（可选，单文件时生效，默认使用文件名）" />
          </div>
          <div class="mb-4">
            <label class="block text-gray-700 text-sm font-bold mb-2">选择文件 <span class="text-red-500">*</span></label>
            <div class="w-full border-2 border-dashed border-gray-300 rounded-lg p-6 text-center hover:border-blue-500 transition-all cursor-pointer"
              @click="triggerFileInput" 
              @dragover.prevent 
              @drop.prevent="handleFileDrop">
              <input type="file" multiple @change="handleFileChange" class="hidden" ref="fileInput" />
              <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12" />
              </svg>
              <p class="mt-2 text-sm text-gray-600">点击或拖拽文件到此处上传</p>
              <p class="text-xs text-gray-500 mt-1">支持 PDF、Word、PPT、图片等格式，可一次多选，也可重复添加</p>
            </div>
            <div v-if="materialFiles.length > 0" class="mt-4 rounded-xl border border-blue-100 bg-blue-50/60 p-3 shadow-sm">
              <div class="mb-3 flex items-center justify-between gap-3">
                <div>
                  <p class="text-sm font-semibold text-slate-800">已选文件</p>
                  <p class="text-xs text-slate-500">本次将上传 {{ materialFiles.length }} 个资源</p>
                </div>
                <span class="inline-flex shrink-0 items-center rounded-full bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white">
                  {{ materialFiles.length }} 个
                </span>
              </div>
              <div class="space-y-2">
                <div
                  v-for="(file, index) in materialFiles"
                  :key="`${file.name}-${index}`"
                  class="flex items-center justify-between gap-3 rounded-lg border border-white/80 bg-white px-3 py-3 text-sm shadow-sm"
                >
                  <div class="min-w-0 flex-1">
                    <p class="truncate font-medium text-slate-700">
                      {{ file.name }}
                    </p>
                    <p class="mt-1 text-xs text-slate-500">
                      {{ (file.size / 1024).toFixed(1) }} KB
                    </p>
                  </div>
                  <button
                    type="button"
                    @click="removeMaterialFile(index)"
                    class="shrink-0 whitespace-nowrap rounded-md px-2 py-1 text-sm font-medium text-red-500 transition-colors hover:bg-red-50 hover:text-red-700"
                  >
                    移除
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          <div v-if="materialUploadProgress > 0 && materialUploadProgress < 100" class="mb-4">
            <div class="w-full bg-gray-200 rounded-full h-2.5">
              <div class="bg-blue-600 h-2.5 rounded-full" :style="`width: ${materialUploadProgress}%`"></div>
            </div>
            <p class="text-sm text-gray-500 mt-1">上传中... {{ materialUploadProgress }}%</p>
          </div>
          
          <p v-if="materialUploadError" class="text-red-500 mb-4">{{ materialUploadError }}</p>
          
          <div class="flex justify-end gap-2 mt-6">
            <button type="button" @click="closeMaterialModal" class="px-4 py-2 border rounded-md">取消</button>
            <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-md">上传</button>
          </div>
        </form>
      </div>
    </div>

    <div v-if="showMaterialChapterModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <div class="flex items-start justify-between gap-4 mb-4">
          <div>
            <h3 class="text-xl font-bold">读取课件资源生成</h3>
            <p class="mt-1 text-sm text-gray-500">先选择资源类型和课件，再预览生成结果，确认后应用到当前课程章节。</p>
          </div>
          <button type="button" class="text-gray-400 hover:text-gray-600" @click="closeMaterialChapterModal">
            <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-5">
          <button
            type="button"
            @click="switchMaterialChapterSource('pdf')"
            :class="[
              'rounded-lg border p-4 text-left transition',
              materialChapterSourceType === 'pdf' ? 'border-amber-500 bg-amber-50 ring-2 ring-amber-100' : 'border-gray-200 hover:border-gray-300'
            ]"
          >
            <div class="flex items-center justify-between gap-3">
              <div>
                <h4 class="font-semibold text-gray-900">读取 PDF</h4>
                <p class="mt-1 text-sm text-gray-600">默认按整本教材处理，将提取目录并重建整门课程章节。</p>
              </div>
              <span class="rounded-full bg-amber-100 px-3 py-1 text-xs font-medium text-amber-700">整门课</span>
            </div>
          </button>
          <button
            type="button"
            @click="switchMaterialChapterSource('ppt')"
            :class="[
              'rounded-lg border p-4 text-left transition',
              materialChapterSourceType === 'ppt' ? 'border-blue-500 bg-blue-50 ring-2 ring-blue-100' : 'border-gray-200 hover:border-gray-300'
            ]"
          >
            <div class="flex items-center justify-between gap-3">
              <div>
                <h4 class="font-semibold text-gray-900">读取 PPT</h4>
                <p class="mt-1 text-sm text-gray-600">默认按单节课处理，只生成一章内容。生成后可选择覆盖对应章节或新增为新章。</p>
              </div>
              <span class="rounded-full bg-blue-100 px-3 py-1 text-xs font-medium text-blue-700">单节课</span>
            </div>
          </button>
        </div>

        <div class="rounded-lg border border-gray-200 bg-gray-50 p-4 mb-5">
          <div class="flex items-start justify-between gap-4 mb-3">
            <div>
              <h4 class="font-semibold text-gray-900">第 1 步：选择课件资源</h4>
              <p class="mt-1 text-sm text-gray-600">{{ materialChapterHelperText }}</p>
            </div>
            <span
              :class="[
                'rounded-full px-3 py-1 text-xs font-medium',
                materialChapterSourceType === 'pdf' ? 'bg-amber-100 text-amber-700' : 'bg-blue-100 text-blue-700'
              ]"
            >
              {{ materialChapterSourceType === 'pdf' ? '将覆盖全部章节' : '将生成 1 章内容' }}
            </span>
          </div>

          <div v-if="availableGenerationMaterials.length > 0">
            <label class="block text-sm font-medium text-gray-700 mb-2">可用课件</label>
            <select v-model="selectedMaterialGenerationId" class="w-full px-3 py-2 border rounded-md bg-white">
              <option v-for="material in availableGenerationMaterials" :key="material.id" :value="material.id">
                {{ material.title }}
              </option>
            </select>
          </div>
          <div v-else class="rounded-md border border-dashed border-gray-300 bg-white p-4">
            <p class="text-sm text-gray-600">请先在课件资源中上传对应文件。</p>
            <button
              type="button"
              @click="openMaterialUploadFromGeneration"
              class="mt-3 px-4 py-2 bg-blue-600 text-white rounded-md"
            >
              去上传课件
            </button>
          </div>

          <p v-if="materialChapterError" class="mt-3 text-sm text-red-600">{{ materialChapterError }}</p>

          <div class="mt-4 flex justify-end gap-2">
            <button type="button" @click="closeMaterialChapterModal" class="px-4 py-2 border rounded-md">取消</button>
            <button
              type="button"
              @click="previewMaterialChapters"
              class="px-4 py-2 bg-gray-900 text-white rounded-md"
              :disabled="materialChapterPreviewLoading || materialChapterApplyLoading || availableGenerationMaterials.length === 0 || selectedMaterialGenerationId === null"
            >
              {{ materialChapterPreviewLoading ? '预览生成中...' : '预览生成结果' }}
            </button>
          </div>
        </div>

        <div v-if="materialChapterPreview" class="space-y-5">
          <div class="rounded-lg border border-gray-200 bg-white p-4">
            <div class="flex items-center justify-between gap-4 mb-3">
              <div>
                <h4 class="font-semibold text-gray-900">第 2 步：确认生成结果</h4>
                <p class="mt-1 text-sm text-gray-600">
                  {{ materialChapterPreview.source_type === 'pdf' ? '将使用当前 PDF 目录重建课程章节。' : '将使用当前 PPT 内容生成一章。' }}
                </p>
              </div>
              <span class="rounded-full bg-emerald-100 px-3 py-1 text-xs font-medium text-emerald-700">
                共 {{ materialChapterPreview.generated_chapters.length }} {{ materialChapterPreview.source_type === 'pdf' ? '章' : '个生成章' }}
              </span>
            </div>

            <div v-if="materialChapterPreview.warnings.length > 0" class="mb-4 rounded-md border border-amber-200 bg-amber-50 p-3">
              <p class="text-sm font-medium text-amber-800">生成提示</p>
              <ul class="mt-2 space-y-1 text-sm text-amber-700">
                <li v-for="warning in materialChapterPreview.warnings" :key="warning">- {{ warning }}</li>
              </ul>
            </div>

            <div v-if="materialChapterPreview.source_type === 'ppt'" class="mb-4 rounded-md border border-blue-200 bg-blue-50 p-4">
              <p class="text-sm font-medium text-blue-900 mb-3">应用方式</p>
              <div class="space-y-3">
                <label class="flex items-start gap-3 text-sm text-gray-700">
                  <input v-model="materialChapterApplyMode" type="radio" class="mt-1" value="replace_one" :disabled="currentCourseChapters.length === 0" />
                  <span :class="currentCourseChapters.length === 0 ? 'text-gray-400' : ''">
                    覆盖现有章节<span v-if="materialChapterPreview.suggested_target_title" class="text-blue-700">（已匹配：{{ materialChapterPreview.suggested_target_title }}）</span>
                    <span v-else-if="currentCourseChapters.length === 0">（当前暂无可覆盖章节）</span>
                  </span>
                </label>
                <div v-if="materialChapterApplyMode === 'replace_one'" class="pl-6">
                  <select v-model="materialChapterTargetIndex" class="w-full px-3 py-2 border rounded-md bg-white">
                    <option v-for="(chapter, index) in currentCourseChapters" :key="`${chapter.title}-${index}`" :value="index">
                      {{ chapter.title }}
                    </option>
                  </select>
                  <p v-if="materialChapterPreview.match_confidence" class="mt-2 text-xs text-blue-700">
                    自动匹配置信度：{{ (materialChapterPreview.match_confidence * 100).toFixed(0) }}%
                  </p>
                </div>

                <label class="flex items-start gap-3 text-sm text-gray-700">
                  <input v-model="materialChapterApplyMode" type="radio" class="mt-1" value="append_one" />
                  <span>追加为新章</span>
                </label>
              </div>
            </div>

            <div class="space-y-3 max-h-[320px] overflow-y-auto pr-1">
              <details v-if="displayedMaterialPreviewChapters.frontMatter.length > 0" class="overflow-hidden rounded-md border border-amber-200 bg-amber-50/60">
                <summary class="cursor-pointer px-4 py-3 text-left">
                  <div class="flex items-center justify-between gap-4">
                    <div>
                      <p class="font-medium text-amber-900">第一章前置内容</p>
                      <p class="mt-1 text-sm text-amber-700">本次识别出的封面、序、前言等 {{ displayedMaterialPreviewChapters.frontMatter.length }} 项内容已折叠</p>
                    </div>
                    <span class="text-sm text-amber-700">展开查看</span>
                  </div>
                </summary>
                <div class="space-y-3 border-t border-amber-200 px-3 py-3">
                  <div
                    v-for="item in displayedMaterialPreviewChapters.frontMatter"
                    :key="`preview-front-${item.originalIndex}`"
                    class="rounded-md border border-gray-200 bg-white"
                  >
                    <div class="flex items-center justify-between bg-amber-50/70 px-4 py-3">
                      <h5 class="font-medium text-gray-900">{{ item.chapter.title }}</h5>
                      <span class="text-sm text-gray-500">{{ item.chapter.duration }} 分钟</span>
                    </div>
                    <div v-if="item.chapter.sections?.length" class="divide-y">
                      <div v-for="(section, sectionIndex) in item.chapter.sections" :key="`${section.title}-${sectionIndex}`" class="px-4 py-3">
                        <div class="flex items-center justify-between gap-3">
                          <span class="text-sm font-medium text-gray-800">{{ section.title }}</span>
                          <span class="text-xs text-gray-500">{{ section.duration }} 分钟</span>
                        </div>
                        <p v-if="section.content" class="mt-1 text-sm text-gray-500">{{ section.content }}</p>
                      </div>
                    </div>
                    <div v-else class="px-4 py-3 text-sm text-gray-500">未生成小节，将按单章保存。</div>
                  </div>
                </div>
              </details>

              <template v-for="(group, groupIndex) in displayedMaterialPreviewChapters.groups" :key="`preview-group-${group.heading || 'default'}-${groupIndex}`">
                <div v-if="group.heading" class="rounded-xl border border-slate-200 bg-slate-50 px-4 py-3">
                  <div class="flex items-center justify-between gap-3">
                    <div>
                      <p class="text-xs font-semibold tracking-wide text-slate-500">分册 / 分部</p>
                      <h5 class="mt-1 font-medium text-slate-900">{{ group.heading }}</h5>
                    </div>
                    <span class="text-sm text-slate-500">{{ group.items.length }} 章</span>
                  </div>
                </div>

                <div
                  v-for="item in group.items"
                  :key="item.displayKey"
                  class="rounded-md border border-gray-200"
                >
                  <div class="flex items-center justify-between bg-gray-50 px-4 py-3">
                    <h5 class="font-medium text-gray-900">{{ item.chapter.title }}</h5>
                    <span class="text-sm text-gray-500">{{ item.chapter.duration }} 分钟</span>
                  </div>
                  <div v-if="item.chapter.sections?.length" class="divide-y">
                    <div v-for="(section, sectionIndex) in item.chapter.sections" :key="`${section.title}-${sectionIndex}`" class="px-4 py-3">
                      <div class="flex items-center justify-between gap-3">
                        <span class="text-sm font-medium text-gray-800">{{ section.title }}</span>
                        <span class="text-xs text-gray-500">{{ section.duration }} 分钟</span>
                      </div>
                      <p v-if="section.content" class="mt-1 text-sm text-gray-500">{{ section.content }}</p>
                    </div>
                  </div>
                  <div v-else class="px-4 py-3 text-sm text-gray-500">未生成小节，将按单章保存。</div>
                </div>
              </template>
            </div>

            <div class="mt-5 flex justify-end gap-2">
              <button type="button" @click="previewMaterialChapters" class="px-4 py-2 border rounded-md" :disabled="materialChapterPreviewLoading || materialChapterApplyLoading">
                重新预览
              </button>
              <button
                type="button"
                @click="applyMaterialChapters"
                class="px-4 py-2 bg-emerald-600 text-white rounded-md"
                :disabled="materialChapterPreviewLoading || materialChapterApplyLoading"
              >
                {{ materialChapterApplyLoading ? '应用中...' : '应用到章节' }}
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 添加学生模态框 -->
    <div v-if="showAddStudentsModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-lg">
        <div class="mb-4 flex items-start justify-between gap-4">
          <div>
            <h3 class="text-xl font-bold">添加学生到课程</h3>
            <p class="mt-1 text-sm text-gray-500">可手动勾选学生，也可从“我的班级”中一键导入全部学生。</p>
          </div>
          <button
            type="button"
            @click="importMyClassStudents"
            :disabled="importableMyClassStudentCount === 0"
            class="rounded-md bg-amber-500 px-3 py-2 text-sm text-white transition hover:bg-amber-600 disabled:cursor-not-allowed disabled:bg-amber-300"
          >
            导入我的班级全部学生
          </button>
        </div>
        
        <div v-if="availableStudents.length === 0" class="text-center py-10">
          <p class="text-gray-500">没有可添加的学生</p>
        </div>
        
        <div v-else>
          <div class="mb-4">
            <p class="text-sm text-gray-600 mb-2">选择要添加到课程的学生：</p>
            <div class="max-h-60 overflow-y-auto border rounded-md p-2">
              <div 
                v-for="student in availableStudents" 
                :key="student.id"
                class="flex items-center p-2 hover:bg-gray-100 rounded-md cursor-pointer"
                @click="toggleStudentSelection(student.id)"
              >
                <input 
                  type="checkbox" 
                  :checked="selectedStudents.includes(student.id)" 
                  class="mr-3"
                />
                <div>
                  <div class="font-medium">{{ student.name }}</div>
                  <div class="text-sm text-gray-500">{{ student.email }}</div>
                </div>
              </div>
            </div>
          </div>
          
          <div class="flex justify-between items-center mt-4">
            <div class="text-sm text-gray-600">已选择 {{ selectedStudents.length }} 名学生</div>
            <div class="flex gap-2">
              <button type="button" @click="showAddStudentsModal = false" class="px-4 py-2 border rounded-md">取消</button>
              <button 
                @click="addStudents" 
                :disabled="selectedStudents.length === 0"
                :class="[
                  'px-4 py-2 text-white rounded-md',
                  selectedStudents.length === 0 ? 'bg-blue-400 cursor-not-allowed' : 'bg-blue-600 hover:bg-blue-700'
                ]"
              >
                添加
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- 添加章节模态框 -->
    <div v-if="showAddChapterModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h3 class="text-xl font-bold mb-4">添加章节</h3>
        <div class="mb-6">
          <div class="mb-4">
            <label class="block text-gray-700 text-sm font-bold mb-2">章节标题</label>
            <input 
              v-model="newChapter.title" 
              type="text" 
              class="w-full px-3 py-2 border rounded-md" 
              placeholder="输入章节标题"
              required
            />
          </div>
          <div class="mb-4">
            <label class="block text-gray-700 text-sm font-bold mb-2">章节时长（分钟）</label>
            <input 
              v-model="newChapter.duration" 
              type="number" 
              class="w-full px-3 py-2 border rounded-md" 
              placeholder="输入章节时长"
              min="1"
            />
          </div>
          
          <div class="mb-2">
            <div class="flex justify-between items-center">
              <label class="block text-gray-700 text-sm font-bold mb-2">小节列表</label>
              <button 
                @click="addSection" 
                class="text-sm px-2 py-1 bg-blue-600 text-white rounded-md flex items-center"
              >
                <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                  <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
                </svg>
                添加小节
              </button>
            </div>
            
            <div v-if="newChapter.sections.length > 0" class="space-y-4 mt-2">
              <div v-for="(section, index) in newChapter.sections" :key="index" class="border p-4 rounded-md relative">
                <button 
                  @click="removeSection(index)" 
                  class="absolute top-2 right-2 text-red-500 hover:text-red-700"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                  </svg>
                </button>
                <div class="mb-2">
                  <label class="block text-gray-700 text-sm font-bold mb-1">小节标题</label>
                  <input 
                    v-model="section.title" 
                    type="text" 
                    class="w-full px-3 py-2 border rounded-md" 
                    placeholder="输入小节标题"
                  />
                </div>
                <div class="mb-2">
                  <label class="block text-gray-700 text-sm font-bold mb-1">小节时长（分钟）</label>
                  <input 
                    v-model="section.duration" 
                    type="number" 
                    class="w-full px-3 py-2 border rounded-md" 
                    placeholder="输入小节时长"
                    min="1"
                  />
                </div>
                <div>
                  <label class="block text-gray-700 text-sm font-bold mb-1">内容简介</label>
                  <textarea 
                    v-model="section.content" 
                    class="w-full px-3 py-2 border rounded-md" 
                    placeholder="输入小节内容简介"
                    rows="2"
                  ></textarea>
                </div>
              </div>
            </div>
              <div v-else class="text-center py-4 border rounded-md bg-gray-50">
                <p class="text-gray-500">暂无小节，可直接保存或继续添加小节</p>
              </div>
          </div>
        </div>
        
        <div class="sticky bottom-0 -mx-6 -mb-6 mt-6 flex justify-end gap-2 border-t bg-white px-6 py-4">
          <button 
            type="button" 
            @click="cancelAddChapter" 
            class="px-4 py-2 border rounded-md"
          >
            取消
          </button>
          <button 
            type="submit" 
            @click="saveChapter" 
            class="px-4 py-2 bg-blue-600 text-white rounded-md"
            :disabled="!isChapterValid"
          >
            保存
          </button>
        </div>
      </div>
    </div>
    
    <!-- 评估编辑模态框 -->
    <div v-if="showAssessmentEditor" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <AssessmentEditor 
          :assessment="currentAssessment"
          @save="handleSaveAssessment"
          @cancel="showAssessmentEditor = false"
        />
      </div>
    </div>
    
    <!-- 修改章节模态框 -->
    <div v-if="showEditChapterModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h3 class="text-xl font-bold mb-4">修改章节</h3>
        <div class="mb-6 space-y-6">
          <div v-for="(chapter, chapterIndex) in editChapters" :key="`chapter-${chapterIndex}`" class="border p-4 rounded-md">
            <div class="flex justify-between items-center mb-3">
              <h4 class="font-bold">章节 {{ chapterIndex + 1 }}</h4>
              <div class="space-x-2">
                <button
                  @click="removeChapter(chapterIndex)"
                  class="text-red-600 hover:text-red-800"
                >
                  删除章节
                </button>
              </div>
            </div>
            
            <div class="mb-4">
              <label class="block text-gray-700 text-sm font-bold mb-2">章节标题</label>
              <input 
                v-model="chapter.title" 
                type="text" 
                class="w-full px-3 py-2 border rounded-md" 
                placeholder="输入章节标题"
                required
              />
            </div>
            <div class="mb-4">
              <label class="block text-gray-700 text-sm font-bold mb-2">章节时长（分钟）</label>
              <input 
                v-model="chapter.duration" 
                type="number" 
                class="w-full px-3 py-2 border rounded-md" 
                placeholder="输入章节时长"
                min="1"
              />
            </div>
            
            <div class="mb-2">
              <div class="flex justify-between items-center">
                <label class="block text-gray-700 text-sm font-bold mb-2">小节列表</label>
                <button 
                  @click="addSectionToChapter(chapterIndex)" 
                  class="text-sm px-2 py-1 bg-blue-600 text-white rounded-md flex items-center"
                >
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" viewBox="0 0 20 20" fill="currentColor">
                    <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
                  </svg>
                  添加小节
                </button>
              </div>
              
              <div v-if="chapter.sections && chapter.sections.length > 0" class="space-y-4 mt-2">
                <div 
                  v-for="(section, sectionIndex) in chapter.sections" 
                  :key="`section-${chapterIndex}-${sectionIndex}`" 
                  class="border p-4 rounded-md relative"
                >
                  <button 
                    @click="removeSectionFromChapter(chapterIndex, sectionIndex)" 
                    class="absolute top-2 right-2 text-red-500 hover:text-red-700"
                  >
                    <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" viewBox="0 0 20 20" fill="currentColor">
                      <path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd" />
                    </svg>
                  </button>
                  <div class="mb-2">
                    <label class="block text-gray-700 text-sm font-bold mb-1">小节标题</label>
                    <input 
                      v-model="section.title" 
                      type="text" 
                      class="w-full px-3 py-2 border rounded-md" 
                      placeholder="输入小节标题"
                    />
                  </div>
                  <div class="mb-2">
                    <label class="block text-gray-700 text-sm font-bold mb-1">小节时长（分钟）</label>
                    <input 
                      v-model="section.duration" 
                      type="number" 
                      class="w-full px-3 py-2 border rounded-md" 
                      placeholder="输入小节时长"
                      min="1"
                    />
                  </div>
                  <div>
                    <label class="block text-gray-700 text-sm font-bold mb-1">内容简介</label>
                    <textarea 
                      v-model="section.content" 
                      class="w-full px-3 py-2 border rounded-md" 
                      placeholder="输入小节内容简介"
                      rows="2"
                    ></textarea>
                  </div>
                </div>
              </div>
              <div v-else class="text-center py-4 border rounded-md bg-gray-50">
                <p class="text-gray-500">暂无小节，可直接保存或继续添加小节</p>
              </div>
            </div>
          </div>
          
          <div class="flex justify-center">
            <button 
              @click="addNewChapter" 
              class="px-4 py-2 bg-green-600 text-white rounded-md flex items-center"
            >
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" viewBox="0 0 20 20" fill="currentColor">
                <path fill-rule="evenodd" d="M10 3a1 1 0 011 1v5h5a1 1 0 110 2h-5v5a1 1 0 11-2 0v-5H4a1 1 0 110-2h5V4a1 1 0 011-1z" clip-rule="evenodd" />
              </svg>
              添加新章节
            </button>
          </div>
        </div>
        
        <div class="sticky bottom-0 -mx-6 -mb-6 mt-6 flex justify-end gap-2 border-t bg-white px-6 py-4">
          <button 
            type="button" 
            @click="showEditChapterModal = false" 
            class="px-4 py-2 border rounded-md"
          >
            取消
          </button>
          <button 
            type="submit" 
            @click="saveEditedChapters" 
            class="px-4 py-2 bg-blue-600 text-white rounded-md"
            :disabled="!isEditChaptersValid"
          >
            保存
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, computed, onMounted, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { useAuthStore } from '../../stores/auth';
import { courseAPI, materialAPI, assessmentAPI, teacherClassAPI, knowledgeBaseAPI } from '../../api';
import MaterialPreview from './MaterialPreview.vue';
import MarkdownViewer from './MarkdownViewer.vue';
import PdfViewer from './PdfViewer.vue';
import AIAssistant from '../ai/AIAssistant.vue';
import AssessmentEditor from '../assessment/AssessmentEditor.vue';
import NavigationControls from './NavigationControls.vue';
import notificationService from '../../services/notificationService';
import dialogService from '../../services/dialogService';
import { API_BASE_URL } from '@/config/api';
import { getMyClassStudentIds, syncMyClassesCache } from '@/services/myClassService';

const emit = defineEmits<{
  (e: 'preview-mode-change', value: boolean): void;
}>();

// 定义接口
interface Course {
  id: number;
  name: string;
  description: string;
  category?: string;
  difficulty?: string;
  teacher_id?: number;
  teacher_name?: string;
  chapters?: Chapter[];
  is_public?: boolean;
  cover_image?: string;
}

interface Section {
  id?: number;
  title: string;
  duration: number;
  content: string;
  start_page?: number;
}

interface Chapter {
  id?: number;
  title: string;
  duration: number;
  sections: Section[];
  start_page?: number;
  is_front_matter?: boolean;
}

interface Material {
  id: number;
  title: string;
  description: string;
  file_path: string;
  material_type: string;
  size: string;
  upload_date: string;
  knowledge_base_status?: string;
}

type MaterialChapterSourceType = 'pdf' | 'ppt';
type MaterialChapterApplyMode = 'replace_all' | 'replace_one' | 'append_one';

interface MaterialChapterPreviewResponse {
  status: string;
  source_type: MaterialChapterSourceType;
  generation_scope: 'replace_all' | 'single_chapter';
  generated_chapters: Chapter[];
  warnings: string[];
  suggested_target_index?: number;
  suggested_target_title?: string;
  match_confidence?: number;
}

interface IndexedChapter {
  chapter: Chapter;
  originalIndex: number;
  displayKey: string;
}

interface ChapterDisplayGroup {
  heading: string | null;
  items: IndexedChapter[];
}

interface Student {
  id: number;
  name: string;
  email: string;
  progress?: number;
  last_activity?: string;
}

interface Assessment {
  id: number;
  title: string;
  description: string;
  course_id: number;
  total_score: number;
  duration?: number;
  start_date?: string;
  due_date?: string;
  max_attempts?: number;
  is_published: boolean;
  is_active: boolean;
  created_at: string;
  updated_at: string;
  sections?: any[];
  questions?: any[];
  submission_count?: number;
}

// 定义文件类型接口
interface FileType {
  extension: string;
  description: string;
}

// 路由参数
const route = useRoute();
const router = useRouter();
const courseId = computed(() => Number(route.params.id));

// 状态
const authStore = useAuthStore();
const loading = ref(true);
const course = ref<Course | null>(null);
const loadError = ref('');
const materials = ref<Material[]>([]);
const students = ref<Student[]>([]);
const availableStudents = ref<Student[]>([]);
const selectedStudents = ref<number[]>([]);
const isLoadingStudents = ref(false);
const studentError = ref<string | null>(null);
const activeTab = ref('chapters');
const assessments = ref<Assessment[]>([]);

// 模态框状态
const showAddChapterModal = ref(false);
const showAddMaterialModal = ref(false);
const showAddStudentsModal = ref(false);
const showMaterialPreview = ref(false);
const showAssessmentEditor = ref(false);
const previewMaterialId = ref<number | null>(null);
const currentAssessment = ref<any>({});
const showMaterialChapterModal = ref(false);

// 知识库相关
const supportedKnowledgeBaseTypes = ref<FileType[]>([]);
const knowledgeBaseProcessing = ref<Record<number, boolean>>({});
const knowledgePurposeSelection = ref<Record<number, 'general' | 'lesson_plan'>>({});

// 添加缺失的材料上传相关属性
const materialTitle = ref('');
const materialFiles = ref<File[]>([]);
const materialUploadProgress = ref(0);
const materialUploadError = ref('');
const fileInput = ref<HTMLInputElement | null>(null);

// 在状态部分添加
const isGeneratingChapters = ref(false);
const showEditChapterModal = ref(false);
const materialChapterSourceType = ref<MaterialChapterSourceType>('pdf');
const selectedMaterialGenerationId = ref<number | null>(null);
const materialChapterPreview = ref<MaterialChapterPreviewResponse | null>(null);
const materialChapterError = ref('');
const materialChapterPreviewLoading = ref(false);
const materialChapterApplyLoading = ref(false);
const materialChapterApplyMode = ref<MaterialChapterApplyMode>('replace_all');
const materialChapterTargetIndex = ref<number | null>(null);
const myClassStudentIds = ref<number[]>(getMyClassStudentIds(authStore.user?.id ?? null));
const importableMyClassStudentCount = computed(() =>
  availableStudents.value.filter(student => myClassStudentIds.value.includes(student.id)).length
);

function refreshMyClassStudentIds() {
  myClassStudentIds.value = getMyClassStudentIds(authStore.user?.id ?? null);
}

// 选项卡定义
const tabs = [
  { id: 'chapters', name: '章节内容' },
  { id: 'materials', name: '课件资源' },
  { id: 'assessments', name: '评估测验' },
  { id: 'students', name: '学生列表' },
];

// 是否可以编辑课程
const canEdit = computed(() => {
  const user = authStore.user;
  if (!user || !course.value) return false;
  return user.role === 'admin' || user.id === course.value.teacher_id;
});

const currentCourseChapters = computed(() => course.value?.chapters || []);
const displayedCourseChapters = computed(() => splitChaptersForDisplay(currentCourseChapters.value));
const displayedMaterialPreviewChapters = computed(() =>
  splitChaptersForDisplay(materialChapterPreview.value?.generated_chapters || [])
);

const availableGenerationMaterials = computed(() => {
  const allowedExtensions = materialChapterSourceType.value === 'pdf'
    ? ['.pdf']
    : ['.ppt', '.pptx'];

  return materials.value.filter(material => {
    const lowerPath = String(material.file_path || material.title || '').toLowerCase();
    return allowedExtensions.some(extension => lowerPath.endsWith(extension));
  });
});

const materialChapterHelperText = computed(() =>
  materialChapterSourceType.value === 'pdf'
    ? '默认按整本教材处理，将提取目录并重建整门课程章节。'
    : '默认按单节课处理，只生成一章内容。生成后可选择覆盖对应章节或新增为新章。'
);

const frontMatterTitlePatterns = [
  /封面/,
  /前言/,
  /前沿/,
  /序言/,
  /中文版序/,
  /译者序/,
  /出版者的话/,
  /出版社的话/,
  /出版说明/,
  /内容提要/,
  /目录/,
  /扉页/,
  /版权/,
  /关于作者/,
  /作者简介/,
  /致谢/,
  /^preface$/i,
  /^foreword$/i,
  /^contents?$/i,
  /^table of contents$/i,
  /^copyright$/i,
  /^acknowledg(e)?ments?$/i,
];

const partTitlePatterns = [
  /^第[一二三四五六七八九十百零\d]+部分/,
  /^part\s+[ivx\d]+/i,
];

function looksLikeMainChapterTitle(title: string) {
  const text = String(title || '').trim();
  const lowered = text.toLowerCase();
  return Boolean(
    /^第[一二三四五六七八九十百零\d]+章/.test(text) ||
    /^chapter\s+\d+/.test(lowered) ||
    /^\d+\s+[^\d].+/.test(text) ||
    /^\d+[、．.]\s*[^\d].+/.test(text)
  );
}

function looksLikeFrontMatterTitle(title: string) {
  const text = String(title || '').trim();
  return frontMatterTitlePatterns.some(pattern => pattern.test(text));
}

function looksLikePartTitle(title: string) {
  const text = String(title || '').trim();
  return partTitlePatterns.some(pattern => pattern.test(text));
}

function buildIndexedChapter(chapter: Chapter, originalIndex: number, displayKey?: string): IndexedChapter {
  return {
    chapter,
    originalIndex,
    displayKey: displayKey || `${originalIndex}-${chapter.title}`,
  };
}

function expandPartContainer(item: IndexedChapter) {
  const sections = Array.isArray(item.chapter.sections) ? item.chapter.sections : [];
  const expanded: IndexedChapter[] = [];
  let currentChapter: Chapter | null = null;
  let currentIndex = 0;

  const pushCurrentChapter = () => {
    if (!currentChapter) return;
    if (currentChapter.sections.length > 0) {
      currentChapter.duration = currentChapter.sections.reduce((sum, section) => sum + Number(section.duration || 0), 0);
    }
    expanded.push(buildIndexedChapter(currentChapter, item.originalIndex, `${item.originalIndex}-part-${currentIndex}`));
    currentIndex += 1;
  };

  for (const section of sections) {
    if (looksLikeMainChapterTitle(section.title)) {
      pushCurrentChapter();
      currentChapter = {
        title: section.title,
        duration: Number(section.duration || 60),
        sections: [],
        start_page: section.start_page,
      };
      continue;
    }

    if (!currentChapter) {
      continue;
    }

    currentChapter.sections.push({
      title: section.title,
      duration: section.duration,
      content: section.content,
      start_page: section.start_page,
    });
  }

  pushCurrentChapter();
  return expanded;
}

function splitChaptersForDisplay(chapters: Chapter[]) {
  const items: IndexedChapter[] = chapters.map((chapter, originalIndex) => buildIndexedChapter(chapter, originalIndex));
  const firstMainChapterIndex = items.findIndex(item => looksLikeMainChapterTitle(item.chapter.title));
  const frontMatter = items.filter(item => {
    if (item.chapter.is_front_matter) return true;
    return firstMainChapterIndex > 0
      && item.originalIndex < firstMainChapterIndex
      && looksLikeFrontMatterTitle(item.chapter.title);
  });
  const frontMatterIndexes = new Set(frontMatter.map(item => item.originalIndex));
  const main = items.filter(item => !frontMatterIndexes.has(item.originalIndex));
  const groups: ChapterDisplayGroup[] = [];
  let currentGroup: ChapterDisplayGroup | null = null;

  for (const item of main) {
    if (looksLikePartTitle(item.chapter.title)) {
      currentGroup = {
        heading: item.chapter.title,
        items: expandPartContainer(item),
      };
      groups.push(currentGroup);
      continue;
    }

    if (!currentGroup) {
      currentGroup = { heading: null, items: [] };
      groups.push(currentGroup);
    }

    currentGroup.items.push(item);
  }

  const normalizedGroups = groups.filter(group => group.heading || group.items.length > 0);
  return { frontMatter, groups: normalizedGroups };
}

// 监听选项卡变化
watch(activeTab, async (newTab) => {
  if (newTab === 'materials' && course.value?.id) {
    fetchKnowledgeBaseStatus();
  } else if (newTab === 'assessments' && course.value?.id) {
    await fetchAssessments();
  } else if (newTab === 'students' && course.value?.id) {
    await fetchStudents();
  }
});

watch(materialChapterSourceType, () => {
  syncGenerationMaterialSelection();
  resetMaterialChapterPreviewState();
  materialChapterApplyMode.value = materialChapterSourceType.value === 'pdf' ? 'replace_all' : 'append_one';
});

watch(availableGenerationMaterials, () => {
  syncGenerationMaterialSelection();
});

watch(showMaterialPreview, (value) => {
  emit('preview-mode-change', value);
}, { immediate: true });

// 初始化
onMounted(async () => {
  await loadCourseDetailData();
});

async function loadCourseDetailData() {
  try {
    loading.value = true;
    loadError.value = '';
    course.value = null;
    if (authStore.user?.role === 'teacher') {
      try {
        const classResponse = await teacherClassAPI.getClasses() as { classes?: any[] };
        syncMyClassesCache(authStore.user?.id ?? null, classResponse.classes || []);
        refreshMyClassStudentIds();
      } catch (classError) {
        console.error('预加载我的班级失败:', classError);
      }
    }
    await fetchCourse(); // 先获取课程信息
    
    // 课程加载完成后，再获取其他数据
    if (course.value) {
      await Promise.all([
        fetchMaterials(),
        fetchStudents(),
        fetchAssessments(),
        fetchChapters()
      ]);
    }
  } catch (error) {
    console.error('加载数据失败:', error);
    if (!loadError.value) {
      loadError.value = getRequestErrorMessage(error, '课程详情暂时不可用，请稍后重试。');
    }
  } finally {
    loading.value = false;
  }
}

// 获取课程详情
async function fetchCourse() {
  try {
    const response = await courseAPI.getCourse(courseId.value);
    course.value = response as any;
  } catch (error) {
    console.error('获取课程详情失败:', error);
    loadError.value = getRequestErrorMessage(error, '无法加载课程详情，请确认课程仍存在且当前账号有访问权限。');
    throw error;
  }
}

async function retryLoadCourseDetail() {
  await loadCourseDetailData();
}

function goBackToDashboard() {
  if (authStore.user?.role === 'teacher') {
    router.push({ path: '/teacher', query: { activeTab: 'courses' } });
    return;
  }
  if (authStore.user?.role === 'student') {
    router.push({ path: '/student', query: { activeTab: 'courses' } });
    return;
  }
  if (authStore.user?.role === 'admin') {
    router.push('/admin');
    return;
  }
  router.push('/dashboard');
}

// 获取课程材料
async function fetchMaterials() {
  try {
    const response = await materialAPI.getMaterials(courseId.value);
    materials.value = (response as any).materials || [];
    for (const material of materials.value) {
      if (!knowledgePurposeSelection.value[material.id]) {
        knowledgePurposeSelection.value[material.id] = 'general';
      }
    }
  } catch (error) {
    console.error('获取课程材料失败:', error);
  }
}

function getRequestErrorMessage(error: unknown, fallback: string) {
  const responseMessage = (error as any)?.response?.data?.message;
  if (typeof responseMessage === 'string' && responseMessage.trim()) {
    return responseMessage;
  }
  if (error instanceof Error && error.message.trim()) {
    return error.message;
  }
  return fallback;
}

function resetMaterialChapterPreviewState() {
  materialChapterPreview.value = null;
  materialChapterError.value = '';
  materialChapterTargetIndex.value = null;
}

function syncGenerationMaterialSelection() {
  const options = availableGenerationMaterials.value;
  if (options.length === 0) {
    selectedMaterialGenerationId.value = null;
    return;
  }

  const exists = options.some(material => material.id === selectedMaterialGenerationId.value);
  if (!exists) {
    selectedMaterialGenerationId.value = options[0].id;
  }
}

function switchMaterialChapterSource(sourceType: MaterialChapterSourceType) {
  if (materialChapterSourceType.value === sourceType) {
    return;
  }
  materialChapterSourceType.value = sourceType;
}

async function openMaterialChapterModal() {
  if (!course.value) {
    return;
  }

  if (materials.value.length === 0) {
    await fetchMaterials();
  }

  const hasPdf = materials.value.some(material => String(material.file_path || material.title || '').toLowerCase().endsWith('.pdf'));
  const hasPpt = materials.value.some(material => {
    const candidate = String(material.file_path || material.title || '').toLowerCase();
    return candidate.endsWith('.ppt') || candidate.endsWith('.pptx');
  });

  materialChapterSourceType.value = hasPdf ? 'pdf' : 'ppt';
  if (!hasPdf && !hasPpt) {
    materialChapterSourceType.value = 'pdf';
  }

  materialChapterApplyMode.value = materialChapterSourceType.value === 'pdf' ? 'replace_all' : 'append_one';
  resetMaterialChapterPreviewState();
  syncGenerationMaterialSelection();
  showMaterialChapterModal.value = true;
}

function closeMaterialChapterModal() {
  showMaterialChapterModal.value = false;
  materialChapterPreviewLoading.value = false;
  materialChapterApplyLoading.value = false;
  materialChapterApplyMode.value = 'replace_all';
  materialChapterSourceType.value = 'pdf';
  selectedMaterialGenerationId.value = null;
  resetMaterialChapterPreviewState();
}

function openMaterialUploadFromGeneration() {
  showMaterialChapterModal.value = false;
  openMaterialModal();
}

async function previewMaterialChapters() {
  if (selectedMaterialGenerationId.value === null) {
    materialChapterError.value = '请先选择一个课件资源';
    return;
  }

  materialChapterPreviewLoading.value = true;
  materialChapterError.value = '';
  materialChapterPreview.value = null;

  try {
    const response = await materialAPI.previewChaptersFromMaterial(courseId.value, {
      material_id: selectedMaterialGenerationId.value,
      source_type: materialChapterSourceType.value,
    }) as unknown as MaterialChapterPreviewResponse;

    materialChapterPreview.value = response;
    if (response.source_type === 'pdf') {
      materialChapterApplyMode.value = 'replace_all';
      materialChapterTargetIndex.value = null;
    } else if (response.suggested_target_index !== undefined && response.suggested_target_index !== null) {
      materialChapterApplyMode.value = 'replace_one';
      materialChapterTargetIndex.value = response.suggested_target_index;
    } else {
      materialChapterApplyMode.value = 'append_one';
      materialChapterTargetIndex.value = currentCourseChapters.value.length > 0 ? 0 : null;
    }
  } catch (error) {
    console.error('课件资源生成预览失败:', error);
    materialChapterError.value = getRequestErrorMessage(error, '生成预览失败，请稍后重试');
  } finally {
    materialChapterPreviewLoading.value = false;
  }
}

async function applyMaterialChapters() {
  if (!materialChapterPreview.value || selectedMaterialGenerationId.value === null) {
    materialChapterError.value = '请先完成预览';
    return;
  }

  if (materialChapterPreview.value.source_type === 'ppt' && materialChapterApplyMode.value === 'replace_one' && materialChapterTargetIndex.value === null) {
    materialChapterError.value = '请选择要覆盖的章节';
    return;
  }

  const confirmMessage = materialChapterPreview.value.source_type === 'pdf'
    ? '这会使用 PDF 提取出的目录覆盖当前课程的全部章节，是否继续？'
    : materialChapterApplyMode.value === 'replace_one'
      ? `这会使用 PPT 生成结果覆盖章节“${currentCourseChapters.value[materialChapterTargetIndex.value ?? 0]?.title || ''}”，是否继续？`
      : '这会把 PPT 生成的一章追加到当前课程章节末尾，是否继续？';

  const confirmed = await dialogService.warning({
    title: '应用章节生成结果',
    message: confirmMessage,
    confirmText: '确认应用',
    cancelText: '取消'
  });

  if (!confirmed) {
    return;
  }

  materialChapterApplyLoading.value = true;
  materialChapterError.value = '';

  try {
    const previewSourceType = materialChapterPreview.value.source_type;
    const payload: Record<string, any> = {
      material_id: selectedMaterialGenerationId.value,
      source_type: previewSourceType,
      apply_mode: previewSourceType === 'pdf' ? 'replace_all' : materialChapterApplyMode.value,
      generated_chapters: materialChapterPreview.value.generated_chapters,
    };

    if (payload.apply_mode === 'replace_one') {
      payload.target_chapter_index = materialChapterTargetIndex.value;
    }

    const response = await materialAPI.applyChaptersFromMaterial(courseId.value, payload) as any;
    if (!course.value) {
      return;
    }

    course.value = {
      ...course.value,
      chapters: Array.isArray(response?.chapters) ? response.chapters : [],
    };
    await fetchChapters();
    closeMaterialChapterModal();
    notificationService.success('章节更新成功', previewSourceType === 'pdf' ? '已按 PDF 目录重建课程章节' : '已根据 PPT 内容更新课程章节');
  } catch (error) {
    console.error('应用课件资源生成章节失败:', error);
    materialChapterError.value = getRequestErrorMessage(error, '应用章节失败，请稍后重试');
  } finally {
    materialChapterApplyLoading.value = false;
  }
}

// 获取课程学生
async function fetchStudents() {
  try {
    isLoadingStudents.value = true;
    studentError.value = null;
    const response = await courseAPI.getCourseStudents(courseId.value);
    students.value = (response as any).students || [];
  } catch (error) {
    console.error('获取学生列表失败:', error);
    studentError.value = '获取学生列表失败';
  } finally {
    isLoadingStudents.value = false;
  }
}

// 获取可添加的学生
async function fetchAvailableStudents() {
  try {
    isLoadingStudents.value = true;
    const response = await courseAPI.getAvailableStudents(courseId.value);
    availableStudents.value = (response as any).students || [];
  } catch (error) {
    console.error('获取可用学生失败:', error);
  } finally {
    isLoadingStudents.value = false;
  }
}

// 添加学生到课程
async function addStudents() {
  if (selectedStudents.value.length === 0) {
    notificationService.warning('无法添加学生', '请选择至少一名学生');
    return;
  }
  
  try {
    await courseAPI.addStudentsToCourse(courseId.value, selectedStudents.value);
    
    // 关闭模态框
    showAddStudentsModal.value = false;
    
    // 重新获取学生列表
    fetchStudents();
    
    notificationService.success('添加成功', '学生已成功添加到课程');
  } catch (error) {
    console.error('添加学生失败:', error);
    notificationService.error('添加学生失败', '请稍后重试');
  }
}

async function importMyClassStudents() {
  const importableStudentIds = availableStudents.value
    .filter(student => myClassStudentIds.value.includes(student.id))
    .map(student => student.id);

  if (importableStudentIds.length === 0) {
    notificationService.warning('无法导入', '“我的班级”中暂无可导入到当前课程的学生');
    return;
  }

  try {
    await courseAPI.addStudentsToCourse(courseId.value, importableStudentIds);
    showAddStudentsModal.value = false;
    selectedStudents.value = [];
    await fetchStudents();
    notificationService.success('导入成功', `已从“我的班级”导入 ${importableStudentIds.length} 名学生`);
  } catch (error) {
    console.error('导入我的班级学生失败:', error);
    notificationService.error('导入失败', '请稍后重试');
  }
}

// 打开添加学生模态框
function openAddStudentsModal() {
  showAddStudentsModal.value = true;
  selectedStudents.value = [];
  fetchAvailableStudents();
}

// 移除学生
async function confirmRemoveStudent(student: Student) {
  const confirmed = await dialogService.warning({
    title: '移除学生',
    message: `确定要将学生 ${student.name} 从课程中移除吗？`,
    confirmText: '移除',
    cancelText: '取消'
  });
  
  if (confirmed) {
    try {
      await courseAPI.removeStudentFromCourse(courseId.value, student.id);
      fetchStudents();
      notificationService.success('移除成功', `学生 ${student.name} 已从课程中移除`);
    } catch (error) {
      console.error('移除学生失败:', error);
      notificationService.error('移除学生失败', '请稍后重试');
    }
  }
}

// 获取课程评估
async function fetchAssessments() {
  try {
    const response = await assessmentAPI.getAssessments(courseId.value);
    assessments.value = (response as any).assessments || [];
  } catch (error) {
    console.error('获取评估列表失败:', error);
  }
}

// 创建新评估
function createNewAssessment() {
  // 显示模态框并使用 AssessmentEditor 组件
  currentAssessment.value = {
    title: '',
    description: '',
    course_id: courseId.value,
    total_score: 100,
    questions: [],
    is_active: false
  };
  showAssessmentEditor.value = true;
}

// 编辑评估
function editAssessment(assessment: Assessment) {
  currentAssessment.value = { ...assessment };
  showAssessmentEditor.value = true;
}

// 处理保存评估
async function handleSaveAssessment(assessment: any) {
  try {
    if (assessment.id) {
      // 更新现有评估
      await assessmentAPI.updateAssessment(assessment.id, assessment);
      notificationService.success('评估更新成功', `评估 "${assessment.title}" 已更新`);
    } else {
      // 创建评估
      await assessmentAPI.createAssessment(assessment);
      notificationService.success('评估创建成功', `评估 "${assessment.title}" 已创建`);
    }
    showAssessmentEditor.value = false;
    await fetchAssessments();
  } catch (error) {
    console.error('保存评估失败:', error);
    notificationService.error('保存评估失败', '请稍后重试');
  }
}

// 获取知识库支持的文件类型
async function fetchKnowledgeBaseStatus() {
  try {
    const data = await knowledgeBaseAPI.getSupportedFileTypes() as any;
    supportedKnowledgeBaseTypes.value = data.supported_types || [];
  } catch (error) {
    console.error('获取知识库支持的文件类型失败:', error);
  }
}

// 判断文件是否支持添加到知识库
function isSupportedForKnowledgeBase(material: Material): boolean {
  const fileExtension = material.file_path.split('.').pop()?.toLowerCase();
  return supportedKnowledgeBaseTypes.value.some(type => 
    type.extension.toLowerCase().includes(`.${fileExtension}`)
  );
}

// 获取知识库按钮文本
function getKnowledgeBaseButtonText(material: Material): string {
  if (knowledgeBaseProcessing.value[material.id]) {
    return '处理中...';
  }
  
  switch (material.knowledge_base_status) {
    case 'processing':
      return '处理中...';
    case 'completed':
      return '已添加';
    case 'failed':
      return '重新添加';
    default:
      return '添加到知识库';
  }
}

// 判断是否正在处理知识库
function isProcessingKnowledgeBase(material: Material): boolean {
  return material.knowledge_base_status === 'processing';
}

// 添加到知识库
async function addToKnowledgeBase(material: Material) {
  try {
    knowledgeBaseProcessing.value[material.id] = true;
    const selectedPurpose = knowledgePurposeSelection.value[material.id] || 'general';

    const result = await knowledgeBaseAPI.addToKnowledgeBase(
      courseId.value,
      material.file_path,
      selectedPurpose
    ) as any;
    
    if (result.status === 'success') {
      // 更新材料状态
      const updatedMaterials = materials.value.map(m => {
        if (m.id === material.id) {
          return { ...m, knowledge_base_status: 'processing' };
        }
        return m;
      });
      materials.value = updatedMaterials;
      notificationService.success('添加成功', `"${material.title}" 已添加到知识库，正在处理中`);
    } else {
      notificationService.error('添加到知识库失败', result.message || '未知错误');
    }
  } catch (error) {
    console.error('添加到知识库失败:', error);
    notificationService.error('添加到知识库失败', '请稍后重试');
  } finally {
    knowledgeBaseProcessing.value[material.id] = false;
  }
}

// 预览材料
function previewMaterial(materialId: number) {
  previewMaterialId.value = materialId;
  showMaterialPreview.value = true;
}

// 下载材料
function downloadMaterial(materialId: number) {
  materialAPI.downloadMaterial(materialId);
}

// 确认删除材料
function confirmDeleteMaterial(material: Material) {
  dialogService.warning({
    title: '删除材料',
    message: `确定要删除材料 "${material.title}" 吗？`,
    confirmText: '删除',
    cancelText: '取消'
  }).then(confirmed => {
    if (confirmed) {
      deleteMaterial(material.id);
    }
  });
}

// 删除材料
async function deleteMaterial(materialId: number) {
  try {
    await materialAPI.deleteMaterial(materialId);
    const deletedMaterial = materials.value.find(m => m.id === materialId);
    materials.value = materials.value.filter(m => m.id !== materialId);
    notificationService.success('删除成功', `材料 "${deletedMaterial?.title || ''}" 已删除`);
  } catch (error) {
    console.error('删除材料失败:', error);
    notificationService.error('删除材料失败', '请稍后重试');
  }
}

// 格式化日期
function formatDate(dateString?: string): string {
  if (!dateString) return '无';
  const date = new Date(dateString);
  return date.toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  });
}

// 获取材料图标
function getMaterialIcon(type: string): string {
  const icons: Record<string, string> = {
    'pdf': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"></path></svg>',
    'doc': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"></path></svg>',
    'docx': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"></path></svg>',
    'ppt': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"></path></svg>',
    'pptx': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"></path></svg>',
    'xls': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"></path></svg>',
    'xlsx': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"></path></svg>',
    'txt': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"></path></svg>',
    'md': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"></path></svg>',
    'image': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 3a2 2 0 00-2 2v10a2 2 0 002 2h12a2 2 0 002-2V5a2 2 0 00-2-2H4zm12 12H4l4-8 3 6 2-4 3 6z" clip-rule="evenodd"></path></svg>',
    'video': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path d="M2 6a2 2 0 012-2h6a2 2 0 012 2v8a2 2 0 01-2 2H4a2 2 0 01-2-2V6z"></path><path d="M14.553 7.106A1 1 0 0014 8v4a1 1 0 00.553.894l2 1A1 1 0 0018 13V7a1 1 0 00-1.447-.894l-2 1z"></path></svg>',
    'audio': '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M9.383 3.076A1 1 0 0110 4v12a1 1 0 01-1.707.707L4.586 13H2a1 1 0 01-1-1V8a1 1 0 011-1h2.586l3.707-3.707a1 1 0 011.09-.217z" clip-rule="evenodd"></path><path d="M14.657 2.929a1 1 0 011.414 0A9.972 9.972 0 0119 10a9.972 9.972 0 01-2.929 7.071 1 1 0 01-1.414-1.414A7.971 7.971 0 0017 10c0-2.21-.894-4.208-2.343-5.657a1 1 0 010-1.414zm-2.829 2.828a1 1 0 011.415 0A5.983 5.983 0 0115 10a5.984 5.984 0 01-1.757 4.243 1 1 0 01-1.415-1.415A3.984 3.984 0 0013 10a3.983 3.983 0 00-1.172-2.828 1 1 0 010-1.415z" clip-rule="evenodd"></path></svg>',
  };
  
  // 根据文件类型返回相应图标
  if (type.includes('image')) return icons['image'];
  if (type.includes('video')) return icons['video'];
  if (type.includes('audio')) return icons['audio'];
  
  // 根据文件扩展名返回图标
  const extension = type.split('/').pop()?.toLowerCase();
  return icons[extension as string] || '<svg class="w-6 h-6" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4 4a2 2 0 012-2h4.586A2 2 0 0112 2.586L15.414 6A2 2 0 0116 7.414V16a2 2 0 01-2 2H6a2 2 0 01-2-2V4z" clip-rule="evenodd"></path></svg>';
}

// 获取难度文本
function difficultyText(difficulty?: string): string {
  const map: Record<string, string> = {
    'beginner': '初级',
    'intermediate': '中级',
    'advanced': '高级'
  };
  return map[difficulty || 'beginner'] || '初级';
}

// 获取难度样式
function difficultyClass(difficulty?: string): string {
  const map: Record<string, string> = {
    'beginner': 'bg-green-100 text-green-800',
    'intermediate': 'bg-yellow-100 text-yellow-800',
    'advanced': 'bg-red-100 text-red-800'
  };
  return map[difficulty || 'beginner'] || 'bg-green-100 text-green-800';
}

// 获取评估状态文本
const getStatusText = (assessment: Assessment): string => {
  if (!assessment.is_published) return '草稿';
  if (!assessment.is_active) return '未激活';
  
  const now = new Date();
  const startDate = assessment.start_date ? new Date(assessment.start_date) : null;
  const dueDate = assessment.due_date ? new Date(assessment.due_date) : null;
  
  if (startDate && now < startDate) return '未开始';
  if (dueDate && now > dueDate) return '已结束';
  return '进行中';
};

// 获取评估状态样式
const getStatusClass = (assessment: Assessment): string => {
  const status = getStatusText(assessment);
  const classes: Record<string, string> = {
    '草稿': 'bg-gray-100 text-gray-800',
    '未激活': 'bg-gray-100 text-gray-800',
    '未开始': 'bg-yellow-100 text-yellow-800',
    '进行中': 'bg-green-100 text-green-800',
    '已结束': 'bg-red-100 text-red-800'
  };
  return classes[status] || 'bg-gray-100 text-gray-800';
};

const getTotalQuestions = (assessment: Assessment): number => {
  return assessment.questions?.length || 0;
};

const confirmDeleteAssessment = (assessment: Assessment): void => {
  dialogService.warning({
    title: '删除评估',
    message: '确定要删除这个评估吗？',
    confirmText: '删除',
    cancelText: '取消'
  }).then(confirmed => {
    if (confirmed) {
      try {
        assessmentAPI.deleteAssessment(assessment.id);
        assessments.value = assessments.value.filter(a => a.id !== assessment.id);
        notificationService.success('删除成功', `评估 "${assessment.title}" 已删除`);
      } catch (error) {
        console.error('删除评估失败:', error);
        notificationService.error('删除评估失败', '请稍后重试');
      }
    }
  });
};

function mergeMaterialFiles(existingFiles: File[], incomingFiles: File[]) {
  const merged = [...existingFiles];
  const fileKeys = new Set(existingFiles.map(file => `${file.name}::${file.size}::${file.lastModified}`));

  for (const file of incomingFiles) {
    const key = `${file.name}::${file.size}::${file.lastModified}`;
    if (fileKeys.has(key)) {
      continue;
    }
    merged.push(file);
    fileKeys.add(key);
  }

  return merged;
}

function setSelectedMaterialFiles(files: File[], options?: { append?: boolean }) {
  const nextFiles = options?.append ? mergeMaterialFiles(materialFiles.value, files) : files;
  materialFiles.value = nextFiles;
  if (nextFiles.length !== 1) {
    materialTitle.value = '';
    return;
  }

  if (!materialTitle.value.trim()) {
    materialTitle.value = nextFiles[0].name;
  }
}

// 处理文件选择
function handleFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  if (!target.files?.length) {
    return;
  }

  setSelectedMaterialFiles(Array.from(target.files), { append: true });
  target.value = '';
}

function removeMaterialFile(index: number) {
  const nextFiles = [...materialFiles.value];
  nextFiles.splice(index, 1);
  setSelectedMaterialFiles(nextFiles);
}

function openMaterialModal() {
  materialFiles.value = [];
  materialTitle.value = '';
  materialUploadProgress.value = 0;
  materialUploadError.value = '';
  showAddMaterialModal.value = true;
}

function closeMaterialModal() {
  showAddMaterialModal.value = false;
  materialFiles.value = [];
  materialTitle.value = '';
  materialUploadProgress.value = 0;
  materialUploadError.value = '';
}

// 上传材料
async function uploadMaterial() {
  if (materialFiles.value.length === 0 || !course.value) {
    materialUploadError.value = '请选择至少一个文件';
    return;
  }
  
  try {
    materialUploadProgress.value = 5;
    materialUploadError.value = '';

    let completedCount = 0;
    const failedFiles: string[] = [];

    for (const file of materialFiles.value) {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', materialFiles.value.length === 1 && materialTitle.value.trim() ? materialTitle.value.trim() : file.name);

      try {
        await materialAPI.uploadMaterial(courseId.value, formData);
        completedCount += 1;
      } catch (error) {
        console.error('上传课件失败:', file.name, error);
        failedFiles.push(file.name);
      }

      materialUploadProgress.value = Math.round((completedCount + failedFiles.length) / materialFiles.value.length * 100);
    }

    if (failedFiles.length > 0) {
      materialUploadError.value = `${failedFiles.length} 个文件上传失败，请重试`;
    } else {
      notificationService.success('上传成功', `已上传 ${completedCount} 个课件资源`);
      closeMaterialModal();
    }

    await fetchMaterials();
  } catch (error) {
    console.error('批量上传课件失败:', error);
    materialUploadError.value = '上传失败，请重试';
    materialUploadProgress.value = 0;
  }
}

// 切换学生选择状态
function toggleStudentSelection(studentId: number) {
  const index = selectedStudents.value.indexOf(studentId);
  if (index === -1) {
    selectedStudents.value.push(studentId);
  } else {
    selectedStudents.value.splice(index, 1);
  }
}

// 获取课程章节
async function fetchChapters() {
  if (!courseId.value || !course.value) {
    console.error('课程ID或课程对象为空，无法获取章节');
    return;
  }
  
  try {
    console.log('获取章节数据...', courseId.value);
    const response = await fetch(`${API_BASE_URL}/courses/${courseId.value}/chapters`, {
      method: 'GET',
      headers: {
        'Accept': 'application/json'
      },
      mode: 'cors'
    });
    
    if (!response.ok) {
      console.error('获取章节响应错误:', response.status, response.statusText);
      return;
    }
    
    const data = await response.json();
    console.log('章节数据:', data);
    
    if (data.status === 'success' && data.chapters && data.chapters.length > 0) {
      course.value = {
        ...course.value,
        chapters: data.chapters
      };
      console.log('章节数据已更新:', course.value.chapters);
    } else {
      console.log('没有章节数据或数据为空');
      // 确保chapters至少是空数组
      course.value.chapters = course.value.chapters || [];
    }
  } catch (error) {
    console.error('获取章节失败:', error);
    // 确保chapters至少是空数组
    if (course.value) {
      course.value.chapters = course.value.chapters || [];
    }
  }
}

// 使用AI生成章节
async function generateChaptersWithAI() {
  if (!course.value || isGeneratingChapters.value) {
    console.error('课程对象为空或正在生成中，无法生成章节');
    return;
  }
  
  try {
    isGeneratingChapters.value = true;
    
    // 强制删除已有章节文件，以便重新生成
    console.log('清除已有章节数据...');
    try {
      // 首先尝试删除章节文件
      const deleteResponse = await fetch(`${API_BASE_URL}/courses/${courseId.value}/chapters?force=true`, {
        method: 'DELETE',
        mode: 'cors',
        headers: {
          'Accept': 'application/json'
        }
      });
      console.log('删除章节响应:', deleteResponse.status);
    } catch (error) {
      // 忽略删除错误，继续生成
      console.log('删除章节错误 (忽略):', error);
    }
    
    // 生成新章节
    console.log('开始生成章节...');
    const response = await fetch(`${API_BASE_URL}/courses/${courseId.value}/generate-chapters`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json',
        'Cache-Control': 'no-cache'
      },
      mode: 'cors',
      body: JSON.stringify({
        course_name: course.value.name,
        description: course.value.description || ''
      })
    });
    
    if (!response.ok) {
      console.error('生成章节响应错误:', response.status, response.statusText);
      throw new Error(`服务器响应错误: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('生成章节响应:', data);
    
    if (data.status === 'success' && data.chapters) {
      course.value = {
        ...course.value,
        chapters: data.chapters
      };
      console.log('章节数据已更新:', course.value.chapters);
      
      // 保存到服务器以确保持久化
      await saveChaptersToServer();
      notificationService.success('章节生成成功', '已使用AI成功生成课程章节');
    } else {
      notificationService.error('生成章节失败', data.message || '未知错误');
    }
  } catch (error) {
    console.error('生成章节失败:', error);
    notificationService.error('生成章节失败', `请稍后重试: ${error instanceof Error ? error.message : String(error)}`);
  } finally {
    isGeneratingChapters.value = false;
  }
}

// 在script部分的状态定义区域添加
const newChapter = ref<Chapter>({
  title: '',
  duration: 60,
  sections: []
});

const editChapters = ref<Chapter[]>([]);

const isChapterValid = computed(() => {
  return newChapter.value.title.trim() !== '' && 
         newChapter.value.duration > 0 && 
         newChapter.value.sections.every(section => 
           section.title.trim() !== '' && 
           section.duration > 0
         );
});

const isEditChaptersValid = computed(() => {
  return editChapters.value.every(chapter => {
    if (chapter.title.trim() === '' || chapter.duration <= 0) {
      return false;
    }

    const sections = Array.isArray(chapter.sections) ? chapter.sections : [];
    return sections.every(section =>
      section.title.trim() !== '' &&
      section.duration > 0
    );
  });
});

// 重置新章节表单
function resetNewChapter() {
  newChapter.value = {
    title: '',
    duration: 60,
    sections: []
  };
}

// 添加小节到新章节
function addSection() {
  if (!newChapter.value.sections) {
    newChapter.value.sections = [];
  }
  
  newChapter.value.sections.push({
    title: '',
    duration: 20,
    content: ''
  });
}

// 从新章节中移除小节
function removeSection(index: number) {
  if (!newChapter.value.sections) {
    return;
  }
  
  newChapter.value.sections.splice(index, 1);
}

// 取消添加章节
function cancelAddChapter() {
  showAddChapterModal.value = false;
  resetNewChapter();
}

// 保存新章节
async function saveChapter() {
  if (!isChapterValid.value || !course.value) return;
  
  try {
    console.log('保存章节...');
    // 如果课程还没有章节数组，初始化它
    if (!course.value.chapters) {
      course.value.chapters = [];
    }
    
    // 添加新章节
    course.value.chapters.push(JSON.parse(JSON.stringify(newChapter.value)));
    
    // 保存章节到后端
    await saveChaptersToServer();
    console.log('章节保存成功');
    
    // 关闭模态框并重置表单
    showAddChapterModal.value = false;
    resetNewChapter();
    
    notificationService.success('章节添加成功', '新章节已成功添加到课程中');
  } catch (error) {
    console.error('保存章节失败:', error);
    notificationService.error('保存章节失败', '请稍后重试');
  }
}

// 打开编辑章节模态框
function openEditChapterModal() {
  if (course.value && course.value.chapters) {
    // 深拷贝章节，避免直接修改
    editChapters.value = JSON.parse(JSON.stringify(course.value.chapters));
    showEditChapterModal.value = true;
  }
}

// 添加小节到指定章节
function addSectionToChapter(chapterIndex: number) {
  if (!editChapters.value[chapterIndex].sections) {
    editChapters.value[chapterIndex].sections = [];
  }
  
  editChapters.value[chapterIndex].sections.push({
    title: '',
    duration: 20,
    content: ''
  });
}

// 从章节中移除小节
function removeSectionFromChapter(chapterIndex: number, sectionIndex: number) {
  if (!editChapters.value[chapterIndex]?.sections) {
    console.error('章节或小节不存在');
    return;
  }
  
  editChapters.value[chapterIndex].sections.splice(sectionIndex, 1);
}

// 添加新章节（编辑模式）
function addNewChapter() {
  editChapters.value.push({
    title: `第${editChapters.value.length + 1}章`,
    duration: 60,
    sections: [{
      title: '第一节',
      duration: 20,
      content: '简介'
    }]
  });
}

// 移除章节（编辑模式）
function removeChapter(chapterIndex: number) {
  editChapters.value.splice(chapterIndex, 1);
}

// 保存编辑后的章节
async function saveEditedChapters() {
  if (!isEditChaptersValid.value || !course.value) return;
  
  try {
    console.log('保存编辑后的章节...');
    // 更新课程章节
    course.value.chapters = JSON.parse(JSON.stringify(editChapters.value));
    console.log('章节数据已更新:', course.value.chapters);
    
    // 保存章节到后端
    await saveChaptersToServer();
    console.log('编辑后的章节保存成功');
    
    // 关闭模态框
    showEditChapterModal.value = false;
    
    notificationService.success('章节更新成功', '课程章节已成功更新');
  } catch (error) {
    console.error('保存章节失败:', error);
    notificationService.error('保存章节失败', '请稍后重试');
  }
}

// 保存章节到服务器
async function saveChaptersToServer() {
  if (!course.value) {
    console.error('课程对象为空，无法保存');
    notificationService.error('无法保存章节', '课程信息丢失');
    return;
  }
  
  if (!course.value.chapters) {
    course.value.chapters = [];
  }
  
  if(!courseId.value) {
    console.error('课程ID为空，无法保存');
    notificationService.error('无法保存章节', '课程ID丢失');
    return;
  }
  
  console.log('保存章节到服务器...', { courseId: courseId.value, chapters: course.value.chapters });
  try {
    const apiUrl = `${API_BASE_URL}/courses/${courseId.value}/chapters`;
    console.log('发送请求到:', apiUrl);
    
    const response = await fetch(apiUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Accept': 'application/json'
      },
      body: JSON.stringify({
        chapters: course.value.chapters
      }),
      mode: 'cors'
    });
    
    console.log('服务器响应状态:', response.status, response.statusText);
    
    if (!response.ok) {
      console.error('服务器响应错误:', response.status, response.statusText);
      notificationService.error('保存失败', `HTTP错误 ${response.status}`);
      throw new Error(`服务器响应错误: ${response.status}`);
    }
    
    const data = await response.json();
    console.log('服务器响应数据:', data);
    
    if (!data.status || data.status !== 'success') {
      notificationService.error('保存失败', data.message || '未知错误');
      throw new Error(data.message || '保存失败');
    }
    
    // 保存成功后重新获取章节
    await fetchChapters();
    
    return data;
  } catch (error) {
    console.error('保存章节到服务器失败:', error);
    notificationService.error('保存失败', `${error instanceof Error ? error.message : '未知错误'}`);
    throw error;
  }
}

// 触发文件选择框
function triggerFileInput() {
  if (fileInput.value) {
    fileInput.value.click();
  }
}

// 处理拖拽文件
function handleFileDrop(event: DragEvent) {
  if (event.dataTransfer?.files?.length) {
    setSelectedMaterialFiles(Array.from(event.dataTransfer.files), { append: true });
  }
}

// in <script setup> section after router const or other functions
function goLearning(idx: number, pageOverride?: number) {
  const chapter = course.value?.chapters?.[idx];
  const query: Record<string, string | number> = { chapter: idx };
  const startPage = pageOverride || chapter?.start_page;
  if (startPage && startPage > 0) {
    query.page = startPage;
  }
  router.push({ name: 'learning', params: { courseId: courseId.value }, query })
}
</script> 
