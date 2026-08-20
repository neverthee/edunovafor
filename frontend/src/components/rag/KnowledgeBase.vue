<template>
  <div class="space-y-8 pb-12">
    <!-- Header -->
    <div v-if="!props.hideHeader" class="relative overflow-hidden rounded-3xl bg-white p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100">
      <div class="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 opacity-50 blur-3xl"></div>
      <div class="relative z-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 class="text-3xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <span class="text-4xl">📚</span> 知识库管理
          </h2>
          <p class="mt-3 text-base text-slate-500 max-w-xl">
            集中管理教学材料与题库，用于AI备课及智能分析的上下文检索。
          </p>
        </div>
        <div class="flex flex-wrap items-center gap-3">
          <button 
            @click="openUploadModal"
            class="flex items-center gap-2 rounded-2xl bg-indigo-600 px-5 py-2.5 text-sm font-bold text-white shadow-md shadow-indigo-200 transition-all hover:bg-indigo-700 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
            直接上传
          </button>
          <button 
            v-if="canManageKnowledgeBase"
            @click="showImportModal = true"
            class="flex items-center gap-2 rounded-2xl bg-white px-5 py-2.5 text-sm font-bold text-slate-700 border border-slate-200 shadow-sm transition-all hover:bg-slate-50 hover:border-slate-300 active:bg-slate-100"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3-3m3 3V4"></path></svg>
            课件导入
          </button>
          <button
            v-if="canManageKnowledgeBase"
            @click="showImportExampleModal = true"
            class="flex items-center gap-2 rounded-2xl bg-slate-100 px-5 py-2.5 text-sm font-bold text-slate-600 transition-all hover:bg-slate-200 active:bg-slate-300"
          >
            <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
            示例资料
          </button>
        </div>
      </div>
    </div>

    <!-- Filters & Search -->
    <div class="rounded-3xl bg-white p-5 border border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.02)]">
      <div class="flex flex-col lg:flex-row gap-4">
        <div class="flex-1">
          <div class="relative">
            <div class="absolute inset-y-0 left-0 pl-4 flex items-center pointer-events-none text-slate-400">
              <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
            </div>
            <input 
              v-model="searchQuery" 
              type="text" 
              placeholder="搜索文件名或课程名..."
              class="w-full rounded-2xl border-2 border-slate-100 bg-slate-50/50 pl-11 pr-4 py-3 text-sm text-slate-800 placeholder-slate-400 outline-none transition focus:border-indigo-500 focus:bg-white"
            />
          </div>
        </div>
        <div class="flex flex-wrap gap-4">
          <button
            @click="openUploadModal"
            class="flex shrink-0 items-center gap-2 rounded-2xl bg-indigo-600 px-5 py-3 text-sm font-bold text-white shadow-md shadow-indigo-200 transition-all hover:bg-indigo-700 hover:shadow-lg hover:-translate-y-0.5 active:translate-y-0"
          >
            <svg class="h-5 w-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
            上传资料
          </button>
          <div class="w-48">
            <select 
              v-model="filterCourseId"
              class="w-full rounded-2xl border-2 border-slate-100 bg-slate-50/50 px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-indigo-500 focus:bg-white appearance-none cursor-pointer"
            >
              <option value="">所有课程</option>
              <option v-for="course in courses" :key="course.id" :value="course.id">
                {{ course.name }}
              </option>
            </select>
          </div>
          <div class="w-40">
            <select 
              v-model="filterStatus"
              class="w-full rounded-2xl border-2 border-slate-100 bg-slate-50/50 px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-indigo-500 focus:bg-white appearance-none cursor-pointer"
            >
              <option value="">所有状态</option>
              <option value="pending">等待处理</option>
              <option value="processing">处理中</option>
              <option value="completed">已完成</option>
              <option value="failed">处理失败</option>
            </select>
          </div>
          <button 
            @click="refreshKnowledgeBase"
            class="flex flex-shrink-0 items-center justify-center w-[50px] h-[50px] rounded-2xl bg-slate-100 text-slate-600 transition hover:bg-slate-200"
            :disabled="refreshing"
            title="刷新"
          >
            <svg class="w-5 h-5 transition-transform" :class="{ 'animate-spin': refreshing }" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
          </button>
        </div>
      </div>

      <!-- Batch Actions -->
      <div v-if="canManageKnowledgeBase && (selectedItems.length > 0 || hasProcessingItems)" class="flex items-center gap-4 mt-4 pt-4 border-t border-slate-100">
        <div class="flex items-center gap-2 px-2">
          <input 
            type="checkbox" 
            v-model="selectAll"
            @change="toggleSelectAll"
            class="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
            id="selectAllCheckbox"
          />
          <label for="selectAllCheckbox" class="text-sm font-medium text-slate-600 cursor-pointer select-none">全选</label>
        </div>
        
        <div class="flex items-center gap-2 border-l border-slate-200 pl-4">
          <button 
            v-if="selectedItems.length > 0"
            @click="batchDelete"
            class="flex items-center gap-2 rounded-xl bg-rose-50 px-4 py-2 text-sm font-semibold text-rose-600 transition hover:bg-rose-100"
            :disabled="batchDeleting"
          >
            <svg v-if="batchDeleting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            批量删除 ({{ selectedItems.length }})
          </button>

          <button 
            v-if="hasProcessingItems"
            @click="clearQueue"
            class="flex items-center gap-2 rounded-xl bg-amber-50 px-4 py-2 text-sm font-semibold text-amber-600 transition hover:bg-amber-100"
            :disabled="clearingQueue"
          >
            <svg v-if="clearingQueue" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
            <svg v-else class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 8h14M5 8a2 2 0 110-4h14a2 2 0 110 4M5 8v10a2 2 0 002 2h10a2 2 0 002-2V8m-9 4h4"></path></svg>
            清空处理队列
          </button>
        </div>
      </div>
    </div>

    <!-- Stats Overview -->
    <div class="grid grid-cols-1 gap-5 md:grid-cols-4">
      <div class="relative overflow-hidden rounded-3xl bg-white p-6 border border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.02)]">
        <div class="flex items-center gap-4">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
            <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
          </div>
          <div>
            <p class="text-sm font-semibold text-slate-500">总文件数</p>
            <p class="mt-1 text-3xl font-extrabold text-slate-900 font-mono">{{ stats.totalFiles }}</p>
          </div>
        </div>
      </div>
      
      <div class="relative overflow-hidden rounded-3xl bg-white p-6 border border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.02)]">
        <div class="flex items-center gap-4">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
            <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path></svg>
          </div>
          <div>
            <p class="text-sm font-semibold text-slate-500">处理完成</p>
            <p class="mt-1 text-3xl font-extrabold text-slate-900 font-mono">{{ stats.completedFiles }}</p>
          </div>
        </div>
      </div>
      
      <div class="relative overflow-hidden rounded-3xl bg-white p-6 border border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.02)]">
        <div class="flex items-center gap-4">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-amber-50 text-amber-600">
            <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
          </div>
          <div>
            <p class="text-sm font-semibold text-slate-500">处理中</p>
            <p class="mt-1 text-3xl font-extrabold text-slate-900 font-mono">{{ stats.processingFiles }}</p>
          </div>
        </div>
      </div>
      
      <div class="relative overflow-hidden rounded-3xl bg-white p-6 border border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.02)]">
        <div class="flex items-center gap-4">
          <div class="flex h-14 w-14 items-center justify-center rounded-2xl bg-rose-50 text-rose-600">
            <svg class="w-7 h-7" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"></path></svg>
          </div>
          <div>
            <p class="text-sm font-semibold text-slate-500">处理失败</p>
            <p class="mt-1 text-3xl font-extrabold text-slate-900 font-mono">{{ stats.failedFiles }}</p>
          </div>
        </div>
      </div>
    </div>

    <!-- Knowledge List -->
    <div class="rounded-3xl bg-white border border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.02)] overflow-hidden">
      <div class="px-6 py-5 border-b border-slate-100 bg-slate-50/50 flex items-center justify-between">
        <h3 class="text-lg font-bold text-slate-800">文件列表</h3>
        <span class="text-sm font-medium text-slate-500">共 {{ filteredKnowledgeItems.length }} 项</span>
      </div>
      
      <div v-if="loading" class="flex flex-col items-center justify-center py-20">
        <div class="h-10 w-10 animate-spin rounded-full border-4 border-indigo-100 border-t-indigo-600"></div>
        <p class="mt-4 text-sm font-medium text-slate-500 animate-pulse">正在获取列表...</p>
      </div>
      
      <div v-else-if="filteredKnowledgeItems.length === 0" class="flex flex-col items-center justify-center py-20 text-center">
        <div class="flex h-20 w-20 items-center justify-center rounded-full bg-slate-50 mb-6">
          <svg class="w-10 h-10 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
        </div>
        <p class="text-base font-semibold text-slate-600">没有找到相关文件</p>
        <p class="mt-2 text-sm text-slate-400">尝试调整搜索词或分类，或者上传新文件</p>
        <button 
          @click="openUploadModal"
          class="mt-6 font-semibold text-indigo-600 hover:text-indigo-700 underline underline-offset-4 decoration-indigo-200 hover:decoration-indigo-600 transition-colors"
        >
          立即上传
        </button>
      </div>
      
      <div v-else class="divide-y divide-slate-100">
        <div 
          v-for="item in filteredKnowledgeItems" 
          :key="item.id" 
          class="group flex flex-col sm:flex-row sm:items-center justify-between p-6 transition-colors hover:bg-slate-50/80 gap-4"
        >
          <div class="flex items-start flex-1 min-w-0">
            <!-- Checkbox -->
            <div v-if="canManageKnowledgeBase" class="mt-1 mr-4">
              <input 
                type="checkbox" 
                :value="item.id"
                v-model="selectedItemIds"
                class="w-4 h-4 rounded border-slate-300 text-indigo-600 focus:ring-indigo-500"
              />
            </div>
            
            <!-- Icon -->
            <div class="mt-1 mr-4 shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">
              <span v-html="getFileIcon(item.file_path)"></span>
            </div>
            
            <!-- Details -->
            <div class="flex-1 min-w-0">
              <div class="flex flex-wrap items-center gap-2">
                <h4 class="text-base font-bold text-slate-800 truncate max-w-full" :title="getFileName(item.file_path)">
                  {{ getFileName(item.file_path) }}
                </h4>
                <span :class="getStatusBadgeClass(item.status)">
                  {{ getStatusText(item.status) }}
                </span>
                <span class="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-600 border border-slate-200">
                  {{ getPurposeText(item.purpose) }}
                </span>
              </div>
              
              <div class="mt-2 flex flex-wrap items-center text-sm text-slate-500 gap-x-4 gap-y-2">
                <span class="flex items-center gap-1 font-medium text-slate-600">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253"></path></svg>
                  {{ getCourseName(item.course_id) }}
                </span>
                <span class="flex items-center gap-1">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path></svg>
                  {{ getFileSize(item.file_path) }}
                </span>
                <span class="flex items-center gap-1">
                  <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
                  {{ formatDate(item.created_at) }}
                </span>
              </div>
              
              <!-- Progress -->
              <div v-if="item.status === 'processing' && item.progress !== undefined" class="mt-3">
                <div class="flex items-center gap-3">
                  <div class="flex-1 bg-slate-100 rounded-full h-2 overflow-hidden border border-slate-200/50">
                    <div 
                      class="bg-indigo-500 h-full rounded-full transition-all duration-300 relative"
                      :style="`width: ${item.progress}%`"
                    >
                      <div class="absolute inset-0 bg-white/20 animate-[shimmer_1s_infinite_linear] bg-gradient-to-r from-transparent via-white/40 to-transparent -skew-x-12"></div>
                    </div>
                  </div>
                  <span class="text-xs font-bold text-indigo-600">{{ item.progress.toFixed(1) }}%</span>
                </div>
              </div>
              
              <!-- Error -->
              <div v-if="item.status === 'failed' && item.error_message" class="mt-3">
                <p class="text-sm font-medium text-rose-600 bg-rose-50 px-3 py-1.5 rounded-lg inline-block">
                  {{ item.error_message }}
                </p>
              </div>
            </div>
          </div>
          
          <!-- Actions -->
          <div class="flex items-center gap-2 pl-9 sm:pl-0 shrink-0">
            <button 
              v-if="item.status === 'completed'"
              @click="searchInFile(item)"
              class="flex items-center justify-center w-9 h-9 rounded-xl bg-white text-slate-400 border border-slate-200 transition-all hover:bg-indigo-50 hover:text-indigo-600 hover:border-indigo-200 tooltip-trigger"
              title="搜索内容"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
            </button>
            
            <button 
              v-if="canManageKnowledgeBase && item.status === 'failed'"
              @click="retryProcessing(item)"
              class="flex items-center justify-center w-9 h-9 rounded-xl bg-white text-slate-400 border border-slate-200 transition-all hover:bg-amber-50 hover:text-amber-600 hover:border-amber-200 tooltip-trigger"
              title="重试处理"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"></path></svg>
            </button>
            
            <button 
              v-if="canManageKnowledgeBase"
              @click="removeFromKnowledgeBase(item)"
              class="flex items-center justify-center w-9 h-9 rounded-xl bg-white text-slate-400 border border-slate-200 transition-all hover:bg-rose-50 hover:text-rose-600 hover:border-rose-200 tooltip-trigger"
              title="删除"
            >
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
            </button>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <transition name="fade">
      <!-- Upload Modal -->
      <div v-if="showUploadModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="handleCloseUploadModal"></div>
        <div class="relative flex w-full max-w-lg max-h-[85vh] flex-col overflow-hidden rounded-[2rem] bg-white shadow-2xl transform transition-all">
          <div class="absolute right-0 top-0 h-40 w-40 -translate-y-16 translate-x-16 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 opacity-50 blur-3xl"></div>
          
          <div class="relative z-10 px-8 py-8 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
              </div>
              <div>
                <h3 class="text-2xl font-extrabold text-slate-900">上传至知识库</h3>
                <p class="text-sm text-slate-500 mt-1">支持 PDF、DOCX、PPT、TXT、MD，上传后自动完成解析、分块与向量化。</p>
              </div>
            </div>
          </div>
          
          <form @submit.prevent="uploadToKnowledgeBase" class="relative z-10 flex-1 space-y-6 overflow-y-auto overscroll-contain custom-scrollbar bg-slate-50/50 p-8">
            <div class="grid grid-cols-2 gap-5">
              <div>
                <label class="mb-2 block text-sm font-semibold text-slate-700">归属课程 <span class="text-rose-500">*</span></label>
                <select
                  v-model="uploadForm.courseId" 
                  required
                  class="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-slate-800 outline-none transition focus:border-indigo-500 focus:bg-white bg-white appearance-none cursor-pointer"
                >
                  <option value="">选择课程</option>
                  <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
                </select>
              </div>
              <div>
                <label class="mb-2 block text-sm font-semibold text-slate-700">内容用途</label>
                <select
                  v-model="uploadForm.purpose"
                  class="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-slate-800 outline-none transition focus:border-indigo-500 focus:bg-white bg-white appearance-none cursor-pointer"
                >
                  <option value="lesson_plan">备课资料</option>
                  <option value="general">通用资料</option>
                </select>
              </div>
            </div>
            
            <div>
              <label class="mb-2 block text-sm font-semibold text-slate-700">选择文件 <span class="text-rose-500">*</span></label>
              <div class="relative overflow-hidden rounded-2xl border-2 border-dashed border-slate-300 bg-white p-8 transition-colors hover:border-indigo-400 hover:bg-indigo-50/30 group">
                <div class="text-center">
                  <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-full bg-slate-50 text-slate-400 group-hover:bg-indigo-100 group-hover:text-indigo-600 transition-colors mb-4">
                    <svg class="w-8 h-8" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.11 9.9M15 13l-3-3m0 0l-3 3m3-3v12"></path></svg>
                  </div>
                  <p class="text-sm font-semibold text-slate-700">拖拽文件到这里，或 <label for="direct-upload" class="text-indigo-600 cursor-pointer hover:underline">点击浏览</label></p>
                  <p class="mt-1 text-xs text-slate-500">支持一次多选，也可重复添加；重复文件会自动跳过。</p>
                </div>
                <input id="direct-upload" type="file" multiple class="absolute inset-0 opacity-0 cursor-pointer" @change="handleDirectFileChange" accept=".pdf,.docx,.doc,.ppt,.pptx,.txt,.md" />
              </div>
              <div v-if="uploadForm.files.length > 0" class="mt-4 rounded-xl border border-blue-100 bg-blue-50/60 p-3 shadow-sm">
                <div class="mb-3 flex items-center justify-between gap-3">
                  <div>
                    <p class="text-sm font-semibold text-slate-800">已选文件</p>
                    <p class="text-xs text-slate-500">本次将上传 {{ uploadForm.files.length }} 个知识库文件</p>
                  </div>
                  <span class="inline-flex shrink-0 items-center rounded-full bg-blue-600 px-2.5 py-1 text-xs font-semibold text-white">
                    {{ uploadForm.files.length }} 个
                  </span>
                </div>
                <div class="space-y-2">
                  <div
                    v-for="(file, index) in uploadForm.files"
                    :key="`${file.name}-${index}`"
                    class="flex items-center justify-between gap-3 rounded-lg border border-white/80 bg-white px-3 py-3 text-sm shadow-sm"
                  >
                    <div class="min-w-0 flex-1">
                      <p class="truncate font-medium text-slate-700">{{ file.name }}</p>
                      <p class="mt-1 text-xs text-slate-500">{{ (file.size / 1024).toFixed(1) }} KB</p>
                    </div>
                    <button
                      type="button"
                      @click="removeUploadFile(index)"
                      class="shrink-0 whitespace-nowrap rounded-md px-2 py-1 text-sm font-medium text-red-500 transition-colors hover:bg-red-50 hover:text-red-700"
                    >
                      移除
                    </button>
                  </div>
                </div>
              </div>
            </div>

            <div class="rounded-xl border border-indigo-100 bg-indigo-50/70 px-4 py-3 text-sm text-indigo-700">
              文件进入知识库后会自动进入处理队列，后台继续完成解析、分块、向量化；处理进度会展示在下方列表中。
            </div>
            
            <div v-if="uploadProgress > 0 && uploadProgress < 100">
              <div class="flex items-center justify-between mb-1.5">
                <span class="text-sm font-semibold text-indigo-700">正在上传...</span>
                <span class="text-sm font-bold text-indigo-700">{{ uploadProgress }}%</span>
              </div>
              <div class="h-2 w-full rounded-full bg-slate-200 overflow-hidden">
                <div class="h-full rounded-full bg-indigo-500 transition-all duration-300" :style="`width: ${uploadProgress}%`"></div>
              </div>
            </div>
            
            <div v-if="uploadError" class="rounded-xl bg-rose-50 px-4 py-3 text-sm font-medium text-rose-600 flex items-center gap-2">
              <svg class="w-4 h-4 shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              {{ uploadError }}
            </div>
          </form>
          
          <div class="relative z-10 flex items-center justify-end gap-3 px-8 py-6 border-t border-slate-100 bg-white">
            <button type="button" @click="handleCloseUploadModal" class="rounded-xl px-6 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-100">取消</button>
            <button type="submit" @click="uploadToKnowledgeBase" :disabled="uploading" class="flex items-center gap-2 rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-bold text-white shadow-md shadow-indigo-200 transition hover:bg-indigo-700 disabled:opacity-70">
              <svg v-if="uploading" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              {{ uploading ? '上传并入库中...' : '确认上传' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <!-- Import Modal -->
      <div v-if="showImportModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="showImportModal = false"></div>
        <div class="relative w-full max-w-4xl overflow-hidden rounded-[2rem] bg-white shadow-2xl transform transition-all flex flex-col max-h-[85vh]">
          <div class="relative z-10 px-8 py-6 border-b border-slate-100 shrink-0 bg-white">
            <div class="flex items-center gap-3">
              <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-sky-50 text-sky-600">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7H5a2 2 0 00-2 2v9a2 2 0 002 2h14a2 2 0 002-2V9a2 2 0 00-2-2h-3m-1 4l-3 3m0 0l-3 3m3 3V4"></path></svg>
              </div>
              <div>
                <h3 class="text-2xl font-extrabold text-slate-900">从课件导入</h3>
                <p class="text-sm text-slate-500 mt-1">选择已有课件并入库，供AI生成教案</p>
              </div>
            </div>
          </div>
          
          <div class="p-8 bg-slate-50/50 flex-1 overflow-y-auto custom-scrollbar">
            <div class="grid grid-cols-2 gap-5 mb-8">
              <div>
                <label class="mb-2 block text-sm font-semibold text-slate-700">归属课程</label>
                <select 
                  v-model="importForm.courseId" 
                  @change="fetchCourseMaterials"
                  class="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-slate-800 outline-none transition focus:border-sky-500 focus:bg-white bg-white cursor-pointer"
                >
                  <option value="">选择课程以查看课件...</option>
                  <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
                </select>
              </div>
              <div>
                <label class="mb-2 block text-sm font-semibold text-slate-700">内容用途</label>
                <select
                  v-model="importForm.purpose"
                  class="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-slate-800 outline-none transition focus:border-sky-500 focus:bg-white bg-white cursor-pointer"
                >
                  <option value="lesson_plan">备课资料</option>
                  <option value="general">通用资料</option>
                </select>
              </div>
            </div>
            
            <div v-if="courseMaterials.length > 0">
              <h4 class="font-bold text-slate-800 mb-4">可导入文件列表</h4>
              <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
                <div 
                  v-for="material in courseMaterials" 
                  :key="material.id"
                  class="flex items-center justify-between rounded-2xl border border-slate-200 bg-white p-4 transition-all hover:border-sky-300 hover:shadow-md"
                >
                  <div class="flex items-center flex-1 min-w-0 mr-4">
                    <span class="mr-3 shrink-0" v-html="getFileIcon(material.file_path)"></span>
                    <div class="min-w-0">
                      <p class="font-semibold text-slate-800 truncate text-sm" :title="material.title">{{ material.title }}</p>
                      <p class="text-xs text-slate-500 mt-0.5">{{ material.material_type }} · {{ material.size }}</p>
                    </div>
                  </div>
                  <button 
                    v-if="isSupportedForKnowledgeBase(material)"
                    @click="importToKnowledgeBase(material)"
                    class="shrink-0 rounded-lg bg-sky-50 px-3 py-1.5 text-xs font-bold text-sky-600 transition hover:bg-sky-100 disabled:opacity-50"
                    :disabled="isProcessingKnowledgeBase(material)"
                  >
                    {{ getImportButtonText(material) }}
                  </button>
                  <span v-else class="shrink-0 text-xs font-medium text-slate-400 bg-slate-50 px-2 py-1 rounded-md">不支持格式</span>
                </div>
              </div>
            </div>
            <div v-else-if="importForm.courseId" class="flex flex-col items-center justify-center py-16 text-center border-2 border-dashed border-slate-200 rounded-3xl bg-white">
              <div class="flex h-16 w-16 items-center justify-center rounded-full bg-slate-50 mb-4">
                <svg class="w-8 h-8 text-slate-300" fill="none" viewBox="0 0 24 24" stroke="currentColor"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
              </div>
              <p class="text-slate-500 font-medium">该课程暂无课件文件</p>
            </div>
          </div>
          
          <div class="relative z-10 flex items-center justify-end px-8 py-6 border-t border-slate-100 bg-white shrink-0">
            <button @click="showImportModal = false" class="rounded-xl bg-slate-900 px-6 py-2.5 text-sm font-bold text-white transition hover:bg-slate-800">完成</button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <!-- Example Modal -->
      <div v-if="showImportExampleModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="showImportExampleModal = false"></div>
        <div class="relative w-full max-w-lg overflow-hidden rounded-[2rem] bg-white shadow-2xl transform transition-all">
          <div class="relative z-10 px-8 py-8 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-50 text-amber-600">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 10V3L4 14h7v7l9-11h-7z"></path></svg>
              </div>
              <div>
                <h3 class="text-2xl font-extrabold text-slate-900">导入系统示例资料</h3>
              </div>
            </div>
          </div>
          
          <div class="p-8 space-y-6 bg-slate-50/50">
            <div>
              <label class="mb-2 block text-sm font-semibold text-slate-700">归属课程</label>
              <select
                v-model="exampleImportForm.courseId"
                class="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-slate-800 outline-none transition focus:border-amber-500 focus:bg-white bg-white cursor-pointer"
              >
                <option value="">选择课程</option>
                <option v-for="course in courses" :key="course.id" :value="course.id">{{ course.name }}</option>
              </select>
            </div>
            <div>
              <label class="mb-2 block text-sm font-semibold text-slate-700">内容用途</label>
              <select
                v-model="exampleImportForm.purpose"
                class="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-slate-800 outline-none transition focus:border-amber-500 focus:bg-white bg-white cursor-pointer"
              >
                <option value="lesson_plan">备课资料</option>
                <option value="general">通用资料</option>
              </select>
            </div>
            <div class="rounded-xl bg-amber-50/50 p-4 border border-amber-100/50">
              <p class="text-sm text-amber-800 leading-relaxed">此操作将自动扫描 <code>example/</code> 目录下的所有演示文件，并批量压入知识库处理队列，非常适合用于体验与测试。</p>
            </div>
          </div>

          <div class="relative z-10 flex items-center justify-end gap-3 px-8 py-6 border-t border-slate-100 bg-white">
            <button @click="showImportExampleModal = false" class="rounded-xl px-6 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-100">取消</button>
            <button
              @click="importExampleKnowledge"
              :disabled="importingExamples"
              class="flex items-center gap-2 rounded-xl bg-slate-900 px-6 py-2.5 text-sm font-bold text-white transition hover:bg-slate-800 disabled:opacity-70"
            >
              <svg v-if="importingExamples" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              {{ importingExamples ? '导入中...' : '开始导入' }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, onBeforeUnmount, computed, watch } from 'vue';
import { useRoute, useRouter } from 'vue-router';
import { ragAiAPI, materialAPI, courseAPI, knowledgeBaseAPI } from '../../api';
import { useAuthStore } from '../../stores/auth';
import notificationService from '../../services/notificationService';
import dialogService from '../../services/dialogService';

const props = withDefaults(defineProps<{
  hideHeader?: boolean;
}>(), {
  hideHeader: false
});

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();
const isStudentView = computed(() => authStore.user?.role === 'student');
const canManageKnowledgeBase = computed(() => authStore.user?.role === 'teacher' || authStore.user?.role === 'admin');
const assistantPath = computed(() => (isStudentView.value ? '/student' : '/teacher'));

// 类型定义
interface Course {
  id: number;
  name: string;
  is_enrolled?: boolean;
}

interface KnowledgeItem {
  id: number;
  course_id: number | null;
  file_path: string;
  purpose?: 'general' | 'lesson_plan' | string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  progress?: number;
  progress_detail?: {
    stage: string;
    message?: string;
  };
  error_message?: string;
  created_at: string | number;
}

interface Material {
  id: number;
  title: string;
  file_path: string;
  material_type: string;
  size: string;
}

interface ApiResponse<T = any> {
  status: string;
  message?: string;
  data?: T;
}

interface CoursesResponse extends ApiResponse {
  courses?: Course[];
}

interface KnowledgeBaseResponse extends ApiResponse {
  items?: KnowledgeItem[];
}

interface MaterialsResponse extends ApiResponse {
  materials?: Material[];
}

interface UploadResponse extends ApiResponse {
  id?: number;
}

interface MaterialDetailResponse extends ApiResponse {
  file_path?: string;
}

// 搜索和筛选
const searchQuery = ref('');
const filterCourseId = ref('');
const filterStatus = ref('');
const refreshing = ref(false);

// 批量操作
const selectedItemIds = ref<number[]>([]);
const selectAll = ref(false);
const batchDeleting = ref(false);
const clearingQueue = ref(false);

// 模态框状态
const showUploadModal = ref(false);
const showImportModal = ref(false);
const showImportExampleModal = ref(false);
const importingExamples = ref(false);

// 上传相关
const uploading = ref(false);
const uploadProgress = ref(0);
const uploadError = ref('');
const uploadForm = reactive({
  courseId: '',
  files: [] as File[],
  purpose: 'lesson_plan' as 'general' | 'lesson_plan'
});

// 导入相关
const importForm = reactive({
  courseId: '',
  purpose: 'lesson_plan' as 'general' | 'lesson_plan'
});

// 示例资料导入
const exampleImportForm = reactive({
  courseId: '',
  purpose: 'lesson_plan' as 'general' | 'lesson_plan'
});

// 数据
const courses = ref<Course[]>([]);
const knowledgeItems = ref<KnowledgeItem[]>([]);
const courseMaterials = ref<Material[]>([]);
const loading = ref(false);

// 统计
const stats = reactive({
  totalFiles: 0,
  completedFiles: 0,
  processingFiles: 0,
  failedFiles: 0
});

const hasProcessing = computed(() =>
  knowledgeItems.value.some(item => item.status === 'pending' || item.status === 'processing')
);

// 批量操作相关计算属性
const selectedItems = computed(() => 
  knowledgeItems.value.filter(item => selectedItemIds.value.includes(item.id))
);

const hasProcessingItems = computed(() =>
  knowledgeItems.value.some(item => item.status === 'pending' || item.status === 'processing')
);

// 轮询控制
let refreshTimer: number | null = null;
let lastRefreshTime = 0;
const REFRESH_INTERVAL = 5000; // 5秒间隔
const MIN_REFRESH_INTERVAL = 1000; // 允许手动操作后更快刷新

// 计算属性
const filteredKnowledgeItems = computed(() => {
  let items = knowledgeItems.value;
  console.log('filteredKnowledgeItems计算开始，原始项目数:', items.length);
  console.log('搜索查询:', searchQuery.value);
  console.log('课程筛选:', filterCourseId.value);
  console.log('状态筛选:', filterStatus.value);
  
  // 按搜索查询过滤
  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase();
    items = items.filter(item => 
      getFileName(item.file_path).toLowerCase().includes(query) ||
      getCourseName(item.course_id).toLowerCase().includes(query)
    );
    console.log('搜索过滤后项目数:', items.length);
  }
  
  // 按课程过滤
  if (filterCourseId.value) {
    items = items.filter(item => item.course_id === Number(filterCourseId.value));
    console.log('课程过滤后项目数:', items.length);
  }
  
  // 按状态过滤
  if (filterStatus.value) {
    items = items.filter(item => item.status === filterStatus.value);
    console.log('状态过滤后项目数:', items.length);
  }
  
  console.log('最终过滤后项目数:', items.length);
  return items;
});

onMounted(async () => {
  console.log('KnowledgeBase组件开始加载...');
  
  // 先获取课程列表
  await fetchCourses();
  console.log('课程列表获取完成，课程数量:', courses.value.length);
  
  // 再获取知识库状态
  await fetchKnowledgeBaseStatus();
  console.log('知识库状态获取完成，知识库项目数量:', knowledgeItems.value.length);
});

onBeforeUnmount(() => {
  document.body.style.overflow = '';
});

watch(hasProcessing, (val) => {
  if (val) {
    if (!refreshTimer) {
      refreshTimer = window.setInterval(() => {
        // 检查是否还有处理中的项目
        if (hasProcessing.value) {
          fetchKnowledgeBaseStatus();
        } else {
          // 如果没有处理中的项目，停止轮询
          if (refreshTimer) {
            clearInterval(refreshTimer);
            refreshTimer = null;
          }
        }
      }, REFRESH_INTERVAL);
    }
  } else {
    // 没有处理中的项目，停止轮询
    if (refreshTimer) {
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  }
}, { immediate: true });

watch(showUploadModal, (visible) => {
  document.body.style.overflow = visible ? 'hidden' : '';
});

// 获取课程列表
async function fetchCourses() {
  try {
    console.log('开始获取课程列表...');
    const response = await courseAPI.getCourses();
    console.log('课程API响应:', response);
    
    // 检查响应格式 - Axios响应
    if (response && typeof response === 'object' && 'data' in response) {
      const data = response.data as CoursesResponse;
      courses.value = data.courses || [];
    } else if (response && typeof response === 'object' && 'courses' in response) {
      // 直接响应格式
      courses.value = (response as CoursesResponse).courses || [];
    } else {
      courses.value = [];
    }

    if (isStudentView.value) {
      courses.value = courses.value.filter(course => course.is_enrolled);
    }
    
    console.log('课程列表设置完成:', courses.value);
  } catch (error) {
    console.error('获取课程列表失败:', error);
    courses.value = [];
  }
}

// 获取知识库状态
async function fetchKnowledgeBaseStatus() {
  // 防抖：如果距离上次请求时间太短，跳过
  const now = Date.now();
  if (now - lastRefreshTime < MIN_REFRESH_INTERVAL) {
    console.log('跳过频繁请求，距离上次请求时间:', now - lastRefreshTime, 'ms');
    return;
  }
  
  lastRefreshTime = now;
  loading.value = true;
  
  try {
    console.log('开始获取全局知识库状态');
    const response = await knowledgeBaseAPI.getKnowledgeBaseStatus();

    if (response && typeof response === 'object' && 'data' in response) {
      const data = response.data as KnowledgeBaseResponse;
      knowledgeItems.value = data?.status === 'success' && Array.isArray(data.items) ? data.items : [];
    } else if (response && typeof response === 'object' && 'status' in response) {
      const kbResponse = response as KnowledgeBaseResponse;
      knowledgeItems.value = kbResponse.status === 'success' && Array.isArray(kbResponse.items) ? kbResponse.items : [];
    } else {
      knowledgeItems.value = [];
    }

    console.log('知识库状态获取完成，总项目数:', knowledgeItems.value.length);
    updateStats();
    console.log('统计更新完成:', stats);
    
    // 检查是否还有处理中的项目，如果没有则停止轮询
    if (!hasProcessing.value && refreshTimer) {
      console.log('所有项目处理完成，停止轮询');
      clearInterval(refreshTimer);
      refreshTimer = null;
    }
  } catch (error) {
    console.error('获取知识库状态失败:', error);
  } finally {
    loading.value = false;
  }
}

// 刷新知识库
async function refreshKnowledgeBase() {
  refreshing.value = true;
  await fetchKnowledgeBaseStatus();
  refreshing.value = false;
}

function resetUploadForm() {
  uploadForm.courseId = '';
  uploadForm.files = [];
  uploadForm.purpose = 'lesson_plan';
  uploadError.value = '';
  uploadProgress.value = 0;
}

function openUploadModal() {
  resetUploadForm();
  if (filterCourseId.value) {
    uploadForm.courseId = String(filterCourseId.value);
  }
  showUploadModal.value = true;
}

function closeUploadModal(force = false) {
  if (uploading.value && !force) return;
  showUploadModal.value = false;
  resetUploadForm();
}

function handleCloseUploadModal() {
  closeUploadModal();
}

function mergeUploadFiles(existingFiles: File[], incomingFiles: File[]) {
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

function removeUploadFile(index: number) {
  const nextFiles = [...uploadForm.files];
  nextFiles.splice(index, 1);
  uploadForm.files = nextFiles;
}

// 更新统计
function updateStats() {
  const items = knowledgeItems.value;
  stats.totalFiles = items.length;
  stats.completedFiles = items.filter(item => item.status === 'completed').length;
  stats.processingFiles = items.filter(item => item.status === 'processing').length;
  stats.failedFiles = items.filter(item => item.status === 'failed').length;
}

// 直接上传到知识库
async function uploadToKnowledgeBase() {
  if (!uploadForm.courseId || uploadForm.files.length === 0) {
    notificationService.warning('操作提示', '请选择课程和文件');
    return;
  }

  uploading.value = true;
  uploadError.value = '';
  uploadProgress.value = 0;

  try {
    let completedCount = 0;
    let duplicateCount = 0;
    let skippedCount = 0;
    const failedFiles: string[] = [];

    for (const [index, file] of uploadForm.files.entries()) {
      try {
        const formData = new FormData();
        formData.append('file', file);
        formData.append('title', file.name);

        uploadProgress.value = Math.round((index / uploadForm.files.length) * 100);

        const uploadResponse = await materialAPI.uploadMaterial(Number(uploadForm.courseId), formData);

        let materialId = 0;
        let isDuplicate = false;
        let duplicateMessage = '';

        if (uploadResponse && typeof uploadResponse === 'object' && 'data' in uploadResponse) {
          const data = uploadResponse.data as any;
          if (data.status === 'duplicate') {
            isDuplicate = true;
            duplicateMessage = data.message || '文件已存在';
            materialId = data.material?.id || 0;
          } else {
            materialId = data.material?.id || 0;
          }
        } else if (uploadResponse && typeof uploadResponse === 'object' && 'status' in uploadResponse) {
          const response = uploadResponse as any;
          if (response.status === 'duplicate') {
            isDuplicate = true;
            duplicateMessage = response.message || '文件已存在';
            materialId = response.material?.id || 0;
          } else {
            materialId = response.material?.id || 0;
          }
        }

        if (!materialId) {
          throw new Error('无法获取上传的文件ID');
        }

        if (isDuplicate) {
          duplicateCount += 1;
          const continueProcessing = await dialogService.confirm({
            title: '重复文件提示',
            message: `${duplicateMessage}\n\n是否继续将该文件添加到知识库？`,
            type: 'info'
          });
          if (!continueProcessing) {
            skippedCount += 1;
            uploadProgress.value = Math.round(((index + 1) / uploadForm.files.length) * 100);
            continue;
          }
        }

        const materialResponse = await materialAPI.getMaterial(materialId);
        let filePath = '';

        if (materialResponse && typeof materialResponse === 'object' && 'data' in materialResponse) {
          const data = materialResponse.data as MaterialDetailResponse;
          filePath = data.file_path || '';
        } else if (materialResponse && typeof materialResponse === 'object' && 'file_path' in materialResponse) {
          filePath = (materialResponse as MaterialDetailResponse).file_path || '';
        }

        if (!filePath) {
          filePath = `materials/${uploadForm.courseId}/${file.name}`;
        }

        filePath = filePath.replace(/^\/?uploads\//, '');
        if (!filePath.startsWith('materials/')) {
          filePath = `materials/${uploadForm.courseId}/${file.name}`;
        }

        const kbResponse = await knowledgeBaseAPI.addToKnowledgeBase(
          Number(uploadForm.courseId),
          filePath,
          uploadForm.purpose
        );

        let success = false;
        let message = '';

        if (kbResponse && typeof kbResponse === 'object' && 'data' in kbResponse) {
          const data = kbResponse.data as ApiResponse;
          success = data.status === 'success';
          message = data.message || '';
        } else if (kbResponse && typeof kbResponse === 'object' && 'status' in kbResponse) {
          const response = kbResponse as ApiResponse;
          success = response.status === 'success';
          message = response.message || '';
        }

        if (!success) {
          throw new Error(message || '添加到知识库失败');
        }

        completedCount += 1;
      } catch (error) {
        console.error('上传到知识库失败:', file.name, error);
        failedFiles.push(file.name);
      }

      uploadProgress.value = Math.round(((index + 1) / uploadForm.files.length) * 100);
    }

    await fetchKnowledgeBaseStatus();

    if (completedCount > 0 && failedFiles.length === 0) {
      closeUploadModal(true);
      const duplicateHint = duplicateCount > 0 ? `，其中 ${duplicateCount} 个为重复文件并已重新入队` : '';
      const skippedHint = skippedCount > 0 ? `，${skippedCount} 个重复文件已跳过` : '';
      notificationService.success('上传成功', `已提交 ${completedCount} 个知识库文件${duplicateHint}${skippedHint}`);
      return;
    }

    if (completedCount > 0) {
      closeUploadModal(true);
      notificationService.warning(
        '部分上传成功',
        `已提交 ${completedCount} 个文件，失败 ${failedFiles.length} 个${skippedCount > 0 ? `，跳过 ${skippedCount} 个` : ''}`
      );
      return;
    }

    if (skippedCount > 0 && failedFiles.length === 0) {
      closeUploadModal(true);
      notificationService.warning('未提交新文件', '选择的重复文件已全部跳过');
      return;
    }

    throw new Error(failedFiles.length > 0 ? `以下文件上传失败：${failedFiles.join('、')}` : '上传失败');
  } catch (error) {
    uploadError.value = error instanceof Error ? error.message : '上传失败';
  } finally {
    uploading.value = false;
    uploadProgress.value = 0;
  }
}

// 处理直接文件选择
function handleDirectFileChange(event: Event) {
  const target = event.target as HTMLInputElement;
  if (target.files && target.files.length > 0) {
    uploadForm.files = mergeUploadFiles(uploadForm.files, Array.from(target.files));
  }
  target.value = '';
}

// 获取课程材料
async function fetchCourseMaterials() {
  if (!importForm.courseId) {
    courseMaterials.value = [];
    return;
  }
  
  try {
    const response = await materialAPI.getMaterials(Number(importForm.courseId));
    
    // 检查响应格式
    if (response && typeof response === 'object' && 'data' in response) {
      const data = response.data as MaterialsResponse;
      courseMaterials.value = data.materials || [];
    } else if (response && typeof response === 'object' && 'materials' in response) {
      courseMaterials.value = (response as MaterialsResponse).materials || [];
    } else {
      courseMaterials.value = [];
    }
  } catch (error) {
    console.error('获取课程材料失败:', error);
    courseMaterials.value = [];
  }
}

// 从课件导入到知识库
async function importToKnowledgeBase(material: Material) {
  if (!material.file_path) {
    notificationService.warning('操作提示', '该材料没有文件路径，无法导入到知识库');
    return;
  }
  // 修正 file_path 路径，去掉 /uploads/ 前缀
  let filePath = material.file_path.replace(/^\/?uploads\//, '');
  try {
    const response = await knowledgeBaseAPI.addToKnowledgeBase(
      Number(importForm.courseId),
      filePath,
      importForm.purpose
    );
    
    // 检查响应格式
    let success = false;
    let message = '';
    
    if (response && typeof response === 'object' && 'data' in response) {
      const data = response.data as ApiResponse;
      success = data.status === 'success';
      message = data.message || '';
    } else if (response && typeof response === 'object' && 'status' in response) {
      const apiResponse = response as ApiResponse;
      success = apiResponse.status === 'success';
      message = apiResponse.message || '';
    }
    
    if (success) {
      await fetchKnowledgeBaseStatus();
      notificationService.success('导入成功', '文件已添加到知识库处理队列');
    } else {
      throw new Error(message || '添加到知识库失败');
    }
  } catch (error) {
    console.error('导入到知识库失败:', error);
    notificationService.error('导入失败', error instanceof Error ? error.message : '未知错误');
  }
}

async function importExampleKnowledge() {
  if (!exampleImportForm.courseId) {
    notificationService.warning('操作提示', '请先选择课程');
    return;
  }

  importingExamples.value = true;
  try {
    const response: any = await knowledgeBaseAPI.importExamples(
      Number(exampleImportForm.courseId),
      exampleImportForm.purpose
    );
    if (response?.status !== 'success') {
      throw new Error(response?.message || '导入示例资料失败');
    }
    await fetchKnowledgeBaseStatus();
    showImportExampleModal.value = false;
    notificationService.success(
      '导入成功',
      `示例资料导入完成：入库 ${response.imported_count || 0}，入队 ${response.queued_count || 0}，跳过 ${response.skipped_count || 0}`
    );
  } catch (error) {
    console.error('导入示例资料失败:', error);
    notificationService.error('导入失败', error instanceof Error ? error.message : '未知错误');
  } finally {
    importingExamples.value = false;
  }
}

// 检查文件是否支持知识库
function isSupportedForKnowledgeBase(material: Material) {
  if (!material.file_path) return false;
  
  const fileExtension = material.file_path.substring(material.file_path.lastIndexOf('.')).toLowerCase();
  return ['.pdf', '.docx', '.doc', '.ppt', '.pptx', '.txt', '.md'].includes(fileExtension);
}

// 检查文件是否正在处理中
function isProcessingKnowledgeBase(material: Material) {
  if (!material.file_path) return false;
  
  const queueItem = knowledgeItems.value.find(item => 
    item.file_path === material.file_path && 
    (item.status === 'pending' || item.status === 'processing')
  );
  
  return !!queueItem;
}

// 获取导入按钮文本
function getImportButtonText(material: Material) {
  if (!material.file_path) return '导入';
  
  const queueItem = knowledgeItems.value.find(item => item.file_path === material.file_path);
  
  if (!queueItem) return '导入';
  
  switch (queueItem.status) {
    case 'pending':
      return '等待处理';
    case 'processing':
      return `处理中 ${queueItem.progress ? queueItem.progress.toFixed(1) : 0}%`;
    case 'completed':
      return '已导入';
    case 'failed':
      return '处理失败';
    default:
      return '导入';
  }
}

// 重试处理
async function retryProcessing(item: KnowledgeItem) {
  try {
    if (item.course_id === null || item.course_id === undefined) {
      notificationService.warning('暂不支持', '该知识库文件缺少来源课程，当前无法直接重试处理。');
      return;
    }

    const result = await dialogService.confirm({
      title: '重试处理',
      message: `确定要重新处理文件 "${getFileName(item.file_path)}" 吗？`,
      type: 'info'
    });
    
    if (!result) return;
    
    const response = await knowledgeBaseAPI.addToKnowledgeBase(
      item.course_id,
      item.file_path,
      (item.purpose === 'lesson_plan' ? 'lesson_plan' : 'general')
    );
    
    // 检查响应格式
    let success = false;
    let message = '';
    
    if (response && typeof response === 'object' && 'data' in response) {
      const data = response.data as ApiResponse;
      success = data.status === 'success';
      message = data.message || '';
    } else if (response && typeof response === 'object' && 'status' in response) {
      const apiResponse = response as ApiResponse;
      success = apiResponse.status === 'success';
      message = apiResponse.message || '';
    }
    
    if (success) {
      await fetchKnowledgeBaseStatus();
      notificationService.success('重试成功', '文件已重新加入处理队列');
    } else {
      throw new Error(message || '重试失败');
    }
  } catch (error) {
    console.error('重试处理失败:', error);
    notificationService.error('重试失败', error instanceof Error ? error.message : '未知错误');
  }
}

// 从知识库删除
async function removeFromKnowledgeBase(item: KnowledgeItem) {
  try {
    const result = await dialogService.confirm({
      title: '删除确认',
      message: `确定要彻底删除文件 "${getFileName(item.file_path)}" 吗？这会同时删除源文件、预览文件、知识库缓存和向量索引，且不可恢复。`,
      type: 'info'
    });
    
    if (!result) return;
    
    const response = await knowledgeBaseAPI.removeFromKnowledgeBase(item.id);
    
    // 检查响应格式
    let success = false;
    let message = '';
    
    if (response && typeof response === 'object' && 'data' in response) {
      const data = response.data as ApiResponse;
      success = data.status === 'success';
      message = data.message || '';
    } else if (response && typeof response === 'object' && 'status' in response) {
      const apiResponse = response as ApiResponse;
      success = apiResponse.status === 'success';
      message = apiResponse.message || '';
    }
    
    if (success) {
      await fetchKnowledgeBaseStatus();
      notificationService.success('删除成功', '文件及其知识库缓存已彻底删除');
    } else {
      throw new Error(message || '删除失败');
    }
  } catch (error) {
    console.error('删除失败:', error);
    notificationService.error('删除失败', error instanceof Error ? error.message : '未知错误');
  }
}

// 在文件中搜索
function searchInFile(item: KnowledgeItem) {
  if (item.status !== 'completed') {
    notificationService.warning('暂不可用', '请等待该文件处理完成后再进入智能助手检索');
    return;
  }

  if (!item.file_path) {
    notificationService.error('跳转失败', '未找到该知识库文件路径');
    return;
  }

  const fileName = getFileName(item.file_path);
  const nextQuery = {
    ...route.query,
    activeTab: 'ai-assistant',
    ragMode: 'file',
    ragAutostart: '1',
    ragFilePath: item.file_path,
    ragFileName: fileName,
    ragPurpose: item.purpose || 'general',
    ragPrompt: `请基于知识库文件《${fileName}》回答，并先概述这份资料的主要内容。`
  } as Record<string, string>;

  if (item.course_id !== null && item.course_id !== undefined) {
    nextQuery.courseId = String(item.course_id);
  } else {
    delete nextQuery.courseId;
  }

  router.push({
    path: assistantPath.value,
    query: nextQuery
  });
}

// 工具函数
function getFileName(filePath: string) {
  if (!filePath) return '未知文件';
  return filePath.substring(filePath.lastIndexOf('/') + 1);
}

function getFileSize(filePath: string) {
  // 这里可以从文件信息中获取实际大小
  return '未知大小';
}

function getCourseName(courseId: number | null) {
  if (courseId === null || courseId === undefined) return '全局知识库';
  const course = courses.value.find(c => c.id === courseId);
  return course ? course.name : `课程 #${courseId}`;
}

function formatDate(dateValue: string | number) {
  if (!dateValue) return '未知时间';
  
  try {
    let timestamp: number;
    
    // 如果是字符串，尝试转换为数字
    if (typeof dateValue === 'string') {
      timestamp = parseInt(dateValue);
      if (isNaN(timestamp)) {
        // 如果不是数字字符串，尝试直接解析日期
        return new Date(dateValue).toLocaleDateString('zh-CN');
      }
    } else {
      timestamp = dateValue;
    }
    
    // 检查是否是Unix时间戳（秒）
    if (timestamp < 10000000000) {
      // 秒级时间戳，转换为毫秒
      timestamp *= 1000;
    }
    
    const date = new Date(timestamp);
    
    // 检查日期是否有效
    if (isNaN(date.getTime())) {
      return '未知时间';
    }
    
    return date.toLocaleDateString('zh-CN');
  } catch (error) {
    console.error('日期格式化错误:', error, '原始值:', dateValue);
    return '未知时间';
  }
}

function getStatusText(status: string) {
  switch (status) {
    case 'pending':
      return '等待处理';
    case 'processing':
      return '处理中';
    case 'completed':
      return '已完成';
    case 'failed':
      return '处理失败';
    default:
      return '未知状态';
  }
}

function getPurposeText(purpose?: string) {
  if (purpose === 'lesson_plan') return '备课';
  return '通用';
}

function getStatusBadgeClass(status: string) {
  switch (status) {
    case 'pending':
      return 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-amber-100 text-amber-800 border border-amber-200';
    case 'processing':
      return 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-indigo-100 text-indigo-800 border border-indigo-200';
    case 'completed':
      return 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-100 text-emerald-800 border border-emerald-200';
    case 'failed':
      return 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-rose-100 text-rose-800 border border-rose-200';
    default:
      return 'px-2.5 py-0.5 text-xs font-semibold rounded-full bg-slate-100 text-slate-800 border border-slate-200';
  }
}

function getFileIcon(filePath: string) {
  if (!filePath) {
    return `<svg class="h-8 w-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
      <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
    </svg>`;
  }
  
  const extension = filePath.substring(filePath.lastIndexOf('.')).toLowerCase();
  
  switch (extension) {
    case '.pdf':
      return `<svg class="h-8 w-8 text-rose-500 drop-shadow-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
      </svg>`;
    case '.docx':
    case '.doc':
      return `<svg class="h-8 w-8 text-indigo-500 drop-shadow-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
      </svg>`;
    case '.txt':
    case '.md':
      return `<svg class="h-8 w-8 text-slate-600 drop-shadow-sm" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path>
      </svg>`;
    default:
      return `<svg class="h-8 w-8 text-slate-400" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M7 21h10a2 2 0 002-2V9.414a1 1 0 00-.293-.707l-5.414-5.414A1 1 0 0012.586 3H7a2 2 0 00-2 2v14a2 2 0 002 2z"></path>
      </svg>`;
  }
}

// 批量操作函数
function toggleSelectAll() {
  if (selectAll.value) {
    selectedItemIds.value = filteredKnowledgeItems.value.map(item => item.id);
  } else {
    selectedItemIds.value = [];
  }
}

async function batchDelete() {
  if (selectedItemIds.value.length === 0) {
    notificationService.warning('操作提示', '请选择要删除的文件');
    return;
  }
  
  try {
    const result = await dialogService.confirm({
      title: '批量删除确认',
      message: `确定要删除选中的 ${selectedItemIds.value.length} 个文件吗？此操作不可恢复。`,
      type: 'info'
    });
    
    if (!result) return;
    
    batchDeleting.value = true;
    const response = await knowledgeBaseAPI.batchRemove(selectedItemIds.value);
    
    // 检查响应格式
    let success = false;
    let message = '';
    
    if (response && typeof response === 'object' && 'data' in response) {
      const data = response.data as ApiResponse;
      success = data.status === 'success';
      message = data.message || '';
    } else if (response && typeof response === 'object' && 'status' in response) {
      const apiResponse = response as ApiResponse;
      success = apiResponse.status === 'success';
      message = apiResponse.message || '';
    }
    
    if (success) {
      selectedItemIds.value = [];
      selectAll.value = false;
      await fetchKnowledgeBaseStatus();
      notificationService.success('批量删除成功', message || '所选文件已删除');
    } else {
      throw new Error(message || '批量删除失败');
    }
  } catch (error) {
    console.error('批量删除失败:', error);
    notificationService.error('批量删除失败', error instanceof Error ? error.message : '未知错误');
  } finally {
    batchDeleting.value = false;
  }
}

async function clearQueue() {
  if (!filterCourseId.value) {
    notificationService.warning('操作提示', '请先选择课程');
    return;
  }
  
  try {
    const result = await dialogService.confirm({
      title: '清空队列确认',
      message: '确定要清空当前课程的所有待处理和处理中的队列吗？此操作不可恢复。',
      type: 'info'
    });
    
    if (!result) return;
    
    clearingQueue.value = true;
    const response = await knowledgeBaseAPI.clearQueue(Number(filterCourseId.value));
    
    // 检查响应格式
    let success = false;
    let message = '';
    
    if (response && typeof response === 'object' && 'data' in response) {
      const data = response.data as ApiResponse;
      success = data.status === 'success';
      message = data.message || '';
    } else if (response && typeof response === 'object' && 'status' in response) {
      const apiResponse = response as ApiResponse;
      success = apiResponse.status === 'success';
      message = apiResponse.message || '';
    }
    
    if (success) {
      await fetchKnowledgeBaseStatus();
      notificationService.success('清空队列成功', message || '队列已清空');
    } else {
      throw new Error(message || '清空队列失败');
    }
  } catch (error) {
    console.error('清空队列失败:', error);
    notificationService.error('清空队列失败', error instanceof Error ? error.message : '未知错误');
  } finally {
    clearingQueue.value = false;
  }
}
</script>

<style scoped>
@keyframes shimmer {
  100% {
    transform: translateX(100%);
  }
}

.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: #cbd5e1;
  border-radius: 20px;
}
.custom-scrollbar::-webkit-scrollbar-thumb:hover {
  background-color: #94a3b8;
}

.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.fade-enter-active .transform,
.fade-leave-active .transform {
  transition: all 0.3s cubic-bezier(0.34, 1.56, 0.64, 1);
}
.fade-enter-from .transform,
.fade-leave-to .transform {
  opacity: 0;
  transform: scale(0.95) translateY(10px);
}

.tooltip-trigger {
  position: relative;
}
.tooltip-trigger::after {
  content: attr(title);
  position: absolute;
  bottom: 110%;
  left: 50%;
  transform: translateX(-50%) scale(0.9);
  padding: 4px 8px;
  border-radius: 6px;
  background-color: #1e293b;
  color: white;
  font-size: 12px;
  font-weight: 500;
  white-space: nowrap;
  opacity: 0;
  visibility: hidden;
  transition: all 0.2s;
  pointer-events: none;
  z-index: 10;
}
.tooltip-trigger:hover::after {
  opacity: 1;
  visibility: visible;
  transform: translateX(-50%) scale(1);
}
</style>
