<template>
  <div class="space-y-8">
    <!-- 欢迎卡片 -->
    <div class="bg-white rounded-2xl border border-slate-100 p-8 shadow-sm relative overflow-hidden group">
      <!-- 装饰背景 -->
      <div class="absolute top-0 right-0 w-64 h-64 bg-blue-50/50 rounded-full blur-3xl -mr-20 -mt-20 transition-all duration-700 group-hover:bg-blue-100/40"></div>
      
      <div class="relative flex flex-col md:flex-row md:items-center gap-6">
        <div class="flex-shrink-0 w-16 h-16 rounded-2xl bg-gradient-to-br from-blue-500 to-indigo-600 flex items-center justify-center shadow-lg shadow-blue-100">
          <svg class="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path v-if="userRole === 'admin'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            <path v-if="userRole === 'teacher'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
            <path v-if="userRole === 'student'" stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
          </svg>
        </div>
        <div class="flex-1">
          <h3 class="text-2xl font-bold text-slate-900 mb-1">
            欢迎回来，{{ userName }}
          </h3>
          <p class="text-slate-500 text-sm">
            {{ welcomeSubtitle }}
          </p>
        </div>
      </div>
    </div>
    
    <!-- 核心功能区 -->
    <div class="space-y-4">
      <div class="flex items-center justify-between px-2">
        <h4 class="text-lg font-bold text-slate-800 flex items-center">
          <span class="w-1.5 h-6 bg-blue-600 rounded-full mr-3"></span>
          {{ quickActionTitle }}
        </h4>
      </div>
      
      <!-- 管理员快速操作 -->
      <div v-if="userRole === 'admin'" class="grid grid-cols-1 md:grid-cols-3 gap-6">
        <button @click="navigate('admin-dashboard')" class="admin-action-card group">
          <div class="action-icon bg-blue-50 text-blue-600">
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
            </svg>
          </div>
          <span class="text-slate-700 font-semibold group-hover:text-blue-600 transition-colors">用户管理</span>
        </button>
        <button @click="navigate('courses')" class="admin-action-card group">
          <div class="action-icon bg-indigo-50 text-indigo-600">
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
            </svg>
          </div>
          <span class="text-slate-700 font-semibold group-hover:text-indigo-600 transition-colors">课程管理</span>
        </button>
        <button @click="navigate('settings')" class="admin-action-card group">
          <div class="action-icon bg-slate-100 text-slate-600">
            <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10.325 4.317c.426-1.756 2.924-1.756 3.35 0a1.724 1.724 0 002.573 1.066c1.543-.94 3.31.826 2.37 2.37a1.724 1.724 0 001.065 2.572c1.756.426 1.756 2.924 0 3.35a1.724 1.724 0 00-1.066 2.573c.94 1.543-.826 3.31-2.37 2.37a1.724 1.724 0 00-2.572 1.065c-.426 1.756-2.924 1.756-3.35 0a1.724 1.724 0 00-2.573-1.066c-1.543.94-3.31-.826-2.37-2.37a1.724 1.724 0 00-1.065-2.572c-1.756-.426-1.756-2.924 0-3.35a1.724 1.724 0 001.066-2.573c-.94-1.543.826-3.31 2.37-2.37.996.608 2.296.07 2.572-1.065z" />
            </svg>
          </div>
          <span class="text-slate-700 font-semibold group-hover:text-slate-900 transition-colors">系统设置</span>
        </button>
      </div>
      
      <!-- 教师快速操作 -->
      <div v-if="userRole === 'teacher'" class="flex flex-col xl:flex-row items-center gap-4 xl:gap-0">
        <!-- 起点组 -->
        <div class="flex flex-col gap-4 w-full xl:w-[28%]">
          <button @click="navigate('courses')" class="workflow-card-minimal group">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-xl bg-indigo-50 text-indigo-600 flex items-center justify-center shrink-0 group-hover:bg-indigo-600 group-hover:text-white transition-all duration-300">
                <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M3 7.5l9-4 9 4m-18 0l9 4m-9-4v9l9 4m0-9l9-4m-9 4v9" />
                </svg>
              </div>
              <div class="text-left">
                <div class="font-bold text-slate-900">我的课程</div>
                <div class="text-xs text-slate-500">资源上传管理</div>
              </div>
            </div>
          </button>
          <button @click="navigate('knowledge-base')" class="workflow-card-minimal group">
            <div class="flex items-center gap-4">
              <div class="w-12 h-12 rounded-xl bg-blue-50 text-blue-600 flex items-center justify-center shrink-0 group-hover:bg-blue-600 group-hover:text-white transition-all duration-300">
                <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
                </svg>
              </div>
              <div class="text-left">
                <div class="font-bold text-slate-900">知识库</div>
                <div class="text-xs text-slate-500">教学资料沉淀</div>
              </div>
            </div>
          </button>
        </div>

        <!-- 间隔箭头 -->
        <div class="hidden xl:flex items-center justify-center w-12 text-slate-300">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </div>

        <!-- 中间步骤：智能备课 -->
        <button @click="navigate('lesson-planner')" class="workflow-step-minimal w-full xl:w-[22%] group">
          <div class="flex flex-col items-center text-center gap-3">
            <div class="w-14 h-14 rounded-2xl bg-amber-50 text-amber-600 flex items-center justify-center shadow-sm group-hover:bg-amber-500 group-hover:text-white transition-all duration-300 group-hover:rotate-6">
              <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M9.663 17h4.673M12 3v1.5m6.364 1.136l-1.06 1.06M21 12h-1.5m-1.136 6.364l-1.06-1.06M12 19.5V21m-6.364-2.636l1.06-1.06M4.5 12H3m2.636-6.364l1.06 1.06M15 12a3 3 0 11-6 0 3 3 0 016 0zm4.5 0a7.5 7.5 0 11-15 0 7.5 7.5 0 0115 0z" />
              </svg>
            </div>
            <div>
              <div class="font-bold text-slate-900 group-hover:text-amber-600 transition-colors">智能备课</div>
              <div class="text-xs text-slate-500 mt-1 px-2">AI辅助生成结构化教案</div>
            </div>
          </div>
        </button>

        <div class="hidden xl:flex items-center justify-center w-12 text-slate-300">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </div>

        <!-- 评估测试 -->
        <button @click="navigate('assessments')" class="workflow-step-minimal w-full xl:w-[22%] group">
          <div class="flex flex-col items-center text-center gap-3">
            <div class="w-14 h-14 rounded-2xl bg-rose-50 text-rose-600 flex items-center justify-center shadow-sm group-hover:bg-rose-500 group-hover:text-white transition-all duration-300 group-hover:rotate-6">
              <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M9 12.75l2.25 2.25L15 9.75M8.25 3.75h7.5A2.25 2.25 0 0118 6v12a2.25 2.25 0 01-2.25 2.25h-7.5A2.25 2.25 0 016 18V6a2.25 2.25 0 012.25-2.25z" />
              </svg>
            </div>
            <div>
              <div class="font-bold text-slate-900 group-hover:text-rose-600 transition-colors">评估测试</div>
              <div class="text-xs text-slate-500 mt-1 px-2">自动测评与反馈</div>
            </div>
          </div>
        </button>

        <div class="hidden xl:flex items-center justify-center w-12 text-slate-300">
          <svg class="w-6 h-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5l7 7-7 7" />
          </svg>
        </div>

        <!-- 学情分析 -->
        <button @click="navigate('analytics')" class="workflow-step-minimal w-full xl:w-[22%] group">
          <div class="flex flex-col items-center text-center gap-3">
            <div class="w-14 h-14 rounded-2xl bg-emerald-50 text-emerald-600 flex items-center justify-center shadow-sm group-hover:bg-emerald-500 group-hover:text-white transition-all duration-300 group-hover:rotate-6">
              <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M3 3v18h18M7.5 15.75l3-3 2.25 2.25 4.5-6 3 2.25" />
              </svg>
            </div>
            <div>
              <div class="font-bold text-slate-900 group-hover:text-emerald-600 transition-colors">学情分析</div>
              <div class="text-xs text-slate-500 mt-1 px-2">多维数据驱动教学</div>
            </div>
          </div>
        </button>
      </div>
      
      <!-- 学生快速操作 -->
      <div v-if="userRole === 'student'" class="grid grid-cols-1 gap-6 xl:grid-cols-[minmax(0,1.3fr)_minmax(320px,0.95fr)]">
        <div class="grid grid-cols-1 gap-6 md:grid-cols-2">
          <button @click="navigate('my-courses')" class="student-action-card group">
            <div class="action-icon bg-blue-50 text-blue-600 group-hover:bg-blue-600 group-hover:text-white transition-all duration-300">
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
              </svg>
            </div>
            <span class="text-slate-700 font-semibold group-hover:text-blue-600 transition-colors">我的课程</span>
            <span class="mt-1 text-xs text-slate-400">已加入课程与学习进度</span>
          </button>

          <button @click="navigate('courses')" class="student-action-card group">
            <div class="action-icon bg-cyan-50 text-cyan-600 group-hover:bg-cyan-600 group-hover:text-white transition-all duration-300">
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 7.5l9-4 9 4m-18 0l9 4m-9-4v9l9 4m0-9l9-4m-9 4v9" />
              </svg>
            </div>
            <span class="text-slate-700 font-semibold group-hover:text-cyan-600 transition-colors">课程目录</span>
            <span class="mt-1 text-xs text-slate-400">发现新课程与学习资源</span>
          </button>

          <button @click="navigate('ai-assistant')" class="student-action-card group">
            <div class="action-icon bg-indigo-50 text-indigo-600 group-hover:bg-indigo-600 group-hover:text-white transition-all duration-300">
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 10h.01M12 10h.01M16 10h.01M9 16H5a2 2 0 01-2-2V6a2 2 0 012-2h14a2 2 0 012 2v8a2 2 0 01-2 2h-5l-5 5v-5z" />
              </svg>
            </div>
            <span class="text-slate-700 font-semibold group-hover:text-indigo-600 transition-colors">智能助手</span>
            <span class="mt-1 text-xs text-slate-400">答疑、练习与学习支持</span>
          </button>

          <button @click="navigate('analytics')" class="student-action-card group">
            <div class="action-icon bg-emerald-50 text-emerald-600 group-hover:bg-emerald-500 group-hover:text-white transition-all duration-300">
              <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
              </svg>
            </div>
            <span class="text-slate-700 font-semibold group-hover:text-emerald-600 transition-colors">学习分析</span>
            <span class="mt-1 text-xs text-slate-400">跟踪表现与进度趋势</span>
          </button>
        </div>

        <button
          @click="navigate('assessments')"
          class="group flex h-full flex-col rounded-3xl border border-slate-100 bg-white p-6 text-left shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
        >
          <div class="flex items-start justify-between gap-4">
            <div>
              <div class="flex items-center gap-3">
                <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-rose-50 text-rose-600 transition-all duration-300 group-hover:bg-rose-500 group-hover:text-white">
                  <svg class="h-6 w-6" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12.75l2.25 2.25L15 9.75M8.25 3.75h7.5A2.25 2.25 0 0118 6v12a2.25 2.25 0 01-2.25 2.25h-7.5A2.25 2.25 0 016 18V6a2.25 2.25 0 012.25-2.25z" />
                  </svg>
                </div>
                <div>
                  <div class="text-lg font-bold text-slate-900">待办事项</div>
                  <div class="text-sm text-slate-500">统一查看待完成评估与作业</div>
                </div>
              </div>
            </div>
            <span class="rounded-full bg-rose-50 px-3 py-1 text-xs font-bold text-rose-600">
              {{ studentTodoLoading ? '加载中' : `${studentTodoItems.length} 项` }}
            </span>
          </div>

          <div class="mt-5 grid grid-cols-2 gap-3">
            <div class="rounded-2xl bg-slate-50 px-4 py-3">
              <div class="text-[11px] font-bold uppercase tracking-wider text-slate-400">待完成评估</div>
              <div class="mt-1 text-2xl font-bold text-slate-900">{{ pendingAssessmentCount }}</div>
            </div>
            <div class="rounded-2xl bg-amber-50/80 px-4 py-3">
              <div class="text-[11px] font-bold uppercase tracking-wider text-amber-500">待提交作业</div>
              <div class="mt-1 text-2xl font-bold text-amber-600">{{ pendingAssignmentCount }}</div>
            </div>
          </div>

          <div class="mt-5 flex-1">
            <div v-if="studentTodoLoading" class="space-y-3">
              <div v-for="index in 3" :key="index" class="h-14 rounded-2xl bg-slate-100/80 animate-pulse"></div>
            </div>
            <div v-else-if="todoPreview.length === 0" class="flex h-full min-h-[176px] flex-col items-center justify-center rounded-2xl border border-dashed border-emerald-200 bg-emerald-50/60 px-4 text-center">
              <div class="text-sm font-semibold text-emerald-700">当前没有待完成任务</div>
              <div class="mt-1 text-xs text-emerald-600">可以继续推进课程学习或查看历史成绩。</div>
            </div>
            <div v-else class="space-y-3">
              <div
                v-for="item in todoPreview"
                :key="item.id"
                class="rounded-2xl border border-slate-100 bg-slate-50/80 px-4 py-3 transition group-hover:border-slate-200"
              >
                <div class="flex items-start justify-between gap-3">
                  <div class="min-w-0">
                    <div class="truncate text-sm font-semibold text-slate-900">{{ item.title }}</div>
                    <div class="mt-1 truncate text-xs text-slate-500">{{ item.courseName }}</div>
                  </div>
                  <span class="shrink-0 rounded-full px-2 py-1 text-[11px] font-bold" :class="todoTypeClass(item.type)">
                    {{ todoTypeText(item.type) }}
                  </span>
                </div>
                <div class="mt-2 text-xs text-slate-500">
                  {{ formatTodoDueDate(item.dueDate) }}
                </div>
              </div>
            </div>
          </div>

          <div class="mt-5 flex items-center justify-between border-t border-slate-100 pt-4 text-sm">
            <span class="text-slate-500">进入任务页继续处理</span>
            <span class="font-semibold text-rose-600">查看全部</span>
          </div>
        </button>
      </div>
    </div>
    
    <!-- 系统概览 -->
    <div class="space-y-6">
      <!-- 状态指示器 -->
      <div class="space-y-4">
        <h4 class="text-lg font-bold text-slate-800 px-2 flex items-center">
          <span class="w-1.5 h-6 bg-slate-400 rounded-full mr-3"></span>
          系统概览
        </h4>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
          <div class="status-pill group">
            <div class="w-1 h-full absolute left-0 top-0 bg-blue-500 transition-all duration-300 group-hover:w-full group-hover:opacity-5 opacity-100"></div>
            <div class="relative">
              <div class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">最近登录</div>
              <div class="text-xs font-bold text-slate-700 mt-0.5 truncate">{{ formatDate(lastLogin).split(' ')[0] }}</div>
            </div>
          </div>
          <div class="status-pill group">
            <div class="w-1 h-full absolute left-0 top-0 bg-emerald-500 transition-all duration-300 group-hover:w-full group-hover:opacity-5 opacity-100"></div>
            <div class="relative">
              <div class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">系统状态</div>
              <div class="text-xs font-bold text-emerald-600 mt-0.5">运行中</div>
            </div>
          </div>
          <div class="status-pill group">
            <div class="w-1 h-full absolute left-0 top-0 bg-purple-500 transition-all duration-300 group-hover:w-full group-hover:opacity-5 opacity-100"></div>
            <div class="relative">
              <div class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">AI模块</div>
              <div class="text-xs font-bold text-purple-600 mt-0.5">已就绪</div>
            </div>
          </div>
          <div class="status-pill group">
            <div class="w-1 h-full absolute left-0 top-0 bg-amber-500 transition-all duration-300 group-hover:w-full group-hover:opacity-5 opacity-100"></div>
            <div class="relative">
              <div class="text-[10px] text-slate-400 font-bold uppercase tracking-wider">未读通知</div>
              <div class="text-xs font-bold text-amber-600 mt-0.5">{{ notificationCount }} 条</div>
            </div>
          </div>
        </div>
      </div>

      <!-- 个人资料 -->
      <div class="space-y-4">
        <div class="flex items-center justify-between px-2">
          <h4 class="text-lg font-bold text-slate-800">个人资料</h4>
          <router-link to="/profile" class="text-xs font-bold text-blue-600 hover:text-blue-700 transition-colors uppercase tracking-widest">
            编辑资料
          </router-link>
        </div>
        <div class="bg-white rounded-2xl border border-slate-100 p-5 shadow-sm hover:shadow-md transition-all duration-300">
          <div class="flex items-center gap-4">
            <div class="w-14 h-14 rounded-2xl bg-slate-100 flex items-center justify-center text-lg font-bold text-slate-500 overflow-hidden shrink-0 border border-slate-50">
              {{ userInitials }}
            </div>
            <div class="min-w-0 flex-1">
              <div class="text-base font-bold text-slate-900 truncate">{{ userName }}</div>
              <div class="text-[11px] text-slate-400 truncate mt-0.5">{{ userEmail }}</div>
              <div class="mt-2">
                <span class="px-2 py-0.5 text-[10px] font-bold rounded-lg border uppercase tracking-wider" 
                  :class="{
                    'bg-emerald-50 text-emerald-600 border-emerald-100': userRole === 'admin',
                    'bg-blue-50 text-blue-600 border-blue-100': userRole === 'teacher',
                    'bg-amber-50 text-amber-600 border-amber-100': userRole === 'student'
                  }">
                  {{ userRoleText }}
                </span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, defineProps, defineEmits, type PropType } from 'vue';
import { useAuthStore } from '@/stores/auth';
import notificationService from '@/services/notificationService';

interface DashboardOverview {
  last_login_at?: string | null;
  notification_count?: number;
}

interface StudentTodoItem {
  id: number;
  title: string;
  description?: string;
  type: string;
  courseId: number;
  courseName: string;
  dueDate?: string | null;
  startDate?: string | null;
}

const props = defineProps({
  activeTab: {
    type: String,
    default: 'dashboard'
  },
  dashboardOverview: {
    type: Object as PropType<DashboardOverview | null>,
    default: null
  },
  studentTodoItems: {
    type: Array as PropType<StudentTodoItem[]>,
    default: () => []
  },
  studentTodoLoading: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['update:activeTab']);

const authStore = useAuthStore();

// 用户信息
const userName = computed(() => authStore.user?.full_name || '用户');
const userEmail = computed(() => authStore.user?.email || '');
const userRole = computed(() => authStore.user?.role || '');
const userRoleText = computed(() => {
  switch (userRole.value) {
    case 'admin': return '管理员';
    case 'teacher': return '教师';
    case 'student': return '学生';
    default: return '用户';
  }
});
const quickActionTitle = computed(() => userRole.value === 'teacher' ? '推荐工作流' : '快速操作');
const userInitials = computed(() => {
  if (!authStore.user?.full_name) return '?';
  return authStore.user.full_name
    .split(' ')
    .map(name => name.charAt(0))
    .join('')
    .toUpperCase();
});
const welcomeSubtitle = computed(() => {
  switch (userRole.value) {
    case 'teacher':
      return '您的智能教学助手已就绪，今天想开启哪项教学任务？';
    case 'student':
      return '学习计划、课程进度和待完成任务已经为您准备好。';
    case 'admin':
      return '系统运行状态、关键数据和管理入口已同步完成。';
    default:
      return '您的智能教学助手已就绪。';
  }
});
const todoPreview = computed(() => props.studentTodoItems.slice(0, 4));
const pendingAssignmentCount = computed(() =>
  props.studentTodoItems.filter(item => item.type === 'assignment').length
);
const pendingAssessmentCount = computed(() =>
  props.studentTodoItems.filter(item => item.type !== 'assignment').length
);

// 系统状态信息
const activeNotificationCount = computed(() => notificationService.getNotifications().value.length);
const lastLogin = computed(() =>
  props.dashboardOverview?.last_login_at ||
  authStore.user?.last_login_at ||
  authStore.user?.updated_at ||
  new Date().toISOString()
);
const notificationCount = computed(() =>
  (props.dashboardOverview?.notification_count || 0) + activeNotificationCount.value
);

// 格式化日期
const formatDate = (dateString: string) => {
  try {
    const date = new Date(dateString);
    return date.toLocaleString('zh-CN', {
      year: 'numeric',
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit'
    });
  } catch (error) {
    return '未知';
  }
};

// 导航方法
const navigate = (tab: string) => {
  emit('update:activeTab', tab);
};

const todoTypeText = (type?: string) => {
  switch (type) {
    case 'assignment':
      return '作业';
    case 'exam':
      return '考试';
    case 'quiz':
      return '测验';
    default:
      return '任务';
  }
};

const todoTypeClass = (type?: string) => {
  switch (type) {
    case 'assignment':
      return 'bg-amber-50 text-amber-600';
    case 'exam':
      return 'bg-rose-50 text-rose-600';
    case 'quiz':
      return 'bg-blue-50 text-blue-600';
    default:
      return 'bg-slate-100 text-slate-600';
  }
};

const formatTodoDueDate = (dateString?: string | null) => {
  if (!dateString) {
    return '无截止时间限制';
  }

  const date = new Date(dateString);
  if (Number.isNaN(date.getTime())) {
    return '截止时间待定';
  }

  return `截止 ${date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit'
  })}`;
};
</script>

<style scoped>
/* 核心功能卡片 */
.admin-action-card, .student-action-card {
  @apply flex flex-col items-center justify-center p-6 bg-white rounded-2xl border border-slate-100 shadow-sm transition-all duration-300 hover:shadow-xl hover:-translate-y-1 active:scale-[0.98];
}

.action-icon {
  @apply w-14 h-14 rounded-2xl flex items-center justify-center mb-4 transition-all duration-500;
}

.student-action-card {
  @apply min-h-[188px] p-5;
}

.student-action-card .action-icon {
  @apply mb-3 h-12 w-12 rounded-xl;
}

/* 教师工作流卡片 - 侧边型 */
.workflow-card-minimal {
  @apply w-full p-4 bg-white rounded-2xl border border-slate-100 shadow-sm transition-all duration-300 hover:shadow-lg hover:border-blue-200 active:scale-[0.98] relative overflow-hidden;
}

/* 教师工作流卡片 - 步骤型 */
.workflow-step-minimal {
  @apply p-6 bg-white rounded-3xl border border-slate-100 shadow-sm transition-all duration-300 hover:shadow-xl hover:border-blue-200 active:scale-[0.98];
}

/* 状态药丸 */
.status-pill {
  @apply relative pl-5 pr-4 py-3 bg-white rounded-2xl border border-slate-50 shadow-sm overflow-hidden transition-all hover:border-slate-200;
}

/* 响应式调整 */
@media (max-width: 1279px) {
  .workflow-step-minimal {
    @apply py-5 px-6 flex-row text-left items-center gap-5;
  }
  .workflow-step-minimal > div {
    @apply flex-row text-left items-center w-full;
  }
}
</style>
