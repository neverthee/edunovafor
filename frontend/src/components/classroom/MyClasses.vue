<template>
  <div class="space-y-8 pb-12">
    <!-- Header -->
    <div v-if="!props.hideHeader" class="relative overflow-hidden rounded-3xl bg-white p-8 shadow-[0_8px_30px_rgb(0,0,0,0.04)] border border-slate-100">
      <div class="absolute -right-20 -top-20 h-64 w-64 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 opacity-50 blur-3xl"></div>
      <div class="relative z-10 flex flex-col gap-6 md:flex-row md:items-center md:justify-between">
        <div>
          <h2 class="text-3xl font-extrabold tracking-tight text-slate-900 flex items-center gap-3">
            <span class="text-4xl">👨‍🏫</span> 我的班级
          </h2>
          <p class="mt-3 text-base text-slate-500 max-w-xl">
            轻松管理班级与学生，为个性化评估与精准教学打下坚实基础。
          </p>
        </div>
        <div class="flex items-center gap-4">
          <div class="flex items-center gap-2 rounded-2xl bg-indigo-50/80 px-5 py-3 text-sm font-medium text-indigo-700 backdrop-blur-sm border border-indigo-100/50">
            <svg class="w-5 h-5 text-indigo-500" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z"></path></svg>
            共 {{ classes.length }} 个班级 · {{ uniqueStudentCount }} 名学生
          </div>
          <button
            @click="openCreateClassModal"
            class="group flex items-center gap-2 rounded-2xl bg-indigo-600 px-6 py-3 text-sm font-bold text-white shadow-lg shadow-indigo-200 transition-all hover:bg-indigo-700 hover:shadow-indigo-300 hover:-translate-y-0.5 active:translate-y-0"
          >
            <svg class="w-5 h-5 transition-transform group-hover:rotate-90" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"></path></svg>
            新建班级
          </button>
        </div>
      </div>
    </div>

    <!-- Minimal Header Fallback -->
    <div v-else class="flex flex-col sm:flex-row items-center justify-between gap-4 bg-white/50 p-4 rounded-2xl border border-slate-100/50 backdrop-blur-md">
      <div class="flex items-center gap-2 text-sm font-medium text-slate-600">
        <span class="w-2 h-2 rounded-full bg-indigo-500 animate-pulse"></span>
        当前数据：{{ classes.length }} 个班级，{{ uniqueStudentCount }} 名学生
      </div>
      <button
        @click="openCreateClassModal"
        class="flex items-center gap-2 rounded-xl bg-slate-900 px-5 py-2.5 text-sm font-semibold text-white transition-all hover:bg-indigo-600 shadow-md hover:shadow-lg"
      >
        <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2.5" d="M12 4v16m8-8H4"></path></svg>
        新建班级
      </button>
    </div>

    <!-- Content Area -->
    <div v-if="loading" class="flex flex-col items-center justify-center py-20">
      <div class="h-12 w-12 animate-spin rounded-full border-4 border-indigo-100 border-t-indigo-600"></div>
      <p class="mt-4 text-sm font-medium text-slate-500 animate-pulse">正在加载班级数据...</p>
    </div>

    <div v-else-if="classes.length === 0" class="flex flex-col items-center justify-center py-24 text-center rounded-3xl border-2 border-dashed border-slate-200 bg-slate-50/50">
      <div class="flex h-20 w-20 items-center justify-center rounded-full bg-indigo-50 mb-6">
        <svg class="w-10 h-10 text-indigo-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.5" d="M19 11H5m14 0a2 2 0 012 2v6a2 2 0 01-2 2H5a2 2 0 01-2-2v-6a2 2 0 012-2m14 0V9a2 2 0 00-2-2M5 11V9a2 2 0 002-2m0 0V5a2 2 0 012-2h6a2 2 0 012 2v2M7 7h10"></path></svg>
      </div>
      <h3 class="text-xl font-bold text-slate-800">还没有创建任何班级</h3>
      <p class="mt-3 text-slate-500 max-w-sm leading-relaxed">你的教学之旅从这里开始。点击上方按钮创建一个班级，然后邀请学生加入吧！</p>
      <button @click="openCreateClassModal" class="mt-8 text-indigo-600 font-semibold hover:text-indigo-700 underline underline-offset-4 decoration-indigo-200 hover:decoration-indigo-600 transition-colors">
        立即创建我的第一个班级
      </button>
    </div>

    <div v-else class="grid grid-cols-1 gap-6 xl:grid-cols-2">
      <div
        v-for="teacherClass in classes"
        :key="teacherClass.id"
        class="group relative overflow-hidden rounded-3xl bg-white p-7 border border-slate-100 shadow-[0_4px_20px_rgb(0,0,0,0.03)] hover:shadow-[0_12px_40px_rgb(0,0,0,0.06)] transition-all duration-300"
      >
        <!-- Card Decorative Background -->
        <div class="absolute right-0 top-0 h-40 w-40 -translate-y-20 translate-x-20 rounded-full bg-gradient-to-br from-indigo-50 to-fuchsia-50 opacity-60 blur-3xl transition-transform duration-700 group-hover:scale-150"></div>
        
        <div class="relative z-10 flex flex-col h-full">
          <!-- Class Header -->
          <div class="flex items-start justify-between gap-4 mb-6">
            <div>
              <div class="flex items-center gap-3 mb-2">
                <h3 class="text-2xl font-bold text-slate-900 tracking-tight">{{ teacherClass.name }}</h3>
                <span class="inline-flex items-center justify-center rounded-full bg-indigo-100/80 px-3 py-1 text-xs font-bold text-indigo-700">
                  {{ teacherClass.student_count }} 人
                </span>
              </div>
              <p class="text-sm text-slate-500 line-clamp-2 leading-relaxed min-h-[2.5rem]">
                {{ teacherClass.description || '一位低调的老师，没有留下班级简介。' }}
              </p>
            </div>
            
            <div class="flex flex-shrink-0 items-center gap-2">
              <button
                @click="openCreateStudentModal(teacherClass)"
                class="flex items-center justify-center w-10 h-10 rounded-xl bg-slate-50 text-indigo-600 transition hover:bg-indigo-50 hover:text-indigo-700 tooltip-trigger"
                title="添加学生"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path></svg>
              </button>
              <button
                @click="confirmDeleteClass(teacherClass)"
                class="flex items-center justify-center w-10 h-10 rounded-xl bg-slate-50 text-rose-500 transition hover:bg-rose-50 hover:text-rose-600 tooltip-trigger"
                title="删除班级"
              >
                <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg>
              </button>
            </div>
          </div>

          <!-- Students List -->
          <div class="flex-1 rounded-2xl bg-slate-50/50 p-5 border border-slate-100/80">
            <div class="flex items-center justify-between mb-4">
              <h4 class="text-sm font-semibold text-slate-700">学生花名册</h4>
              <span class="text-xs text-slate-400">最后更新: {{ formatDate(teacherClass.updated_at || teacherClass.created_at) }}</span>
            </div>

            <div v-if="!teacherClass.students.length" class="flex flex-col items-center justify-center py-8 text-center">
              <span class="text-3xl mb-2 opacity-60">👻</span>
              <p class="text-sm text-slate-400">空空如也，快去邀请学生吧</p>
            </div>

            <div v-else class="space-y-2.5 max-h-[220px] overflow-y-auto pr-2 custom-scrollbar">
              <div
                v-for="student in teacherClass.students"
                :key="student.id"
                class="group/item flex items-center justify-between rounded-xl bg-white p-3 border border-slate-100 shadow-sm transition-all hover:border-indigo-100 hover:shadow-md"
              >
                <div class="flex items-center gap-3">
                  <!-- Avatar -->
                  <div class="flex h-10 w-10 items-center justify-center rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 text-indigo-700 font-bold shadow-inner">
                    {{ (student.full_name || student.username).charAt(0).toUpperCase() }}
                  </div>
                  <div>
                    <p class="text-sm font-bold text-slate-800">{{ student.full_name || student.username }}</p>
                    <p class="text-xs text-slate-400 mt-0.5">{{ student.username }}</p>
                  </div>
                </div>
                
                <button
                  @click="confirmRemoveStudent(teacherClass, student)"
                  class="opacity-0 group-hover/item:opacity-100 flex items-center justify-center rounded-lg bg-rose-50 px-3 py-1.5 text-xs font-semibold text-rose-600 transition-all hover:bg-rose-100"
                >
                  移出
                </button>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>

    <!-- Modals -->
    <transition name="fade">
      <div v-if="showCreateClassModal" class="fixed inset-0 z-50 flex items-center justify-center p-4">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="closeCreateClassModal"></div>
        
        <!-- Modal Content -->
        <div class="relative w-full max-w-lg overflow-hidden rounded-[2rem] bg-white shadow-2xl transform transition-all">
          <div class="absolute right-0 top-0 h-40 w-40 -translate-y-16 translate-x-16 rounded-full bg-gradient-to-br from-indigo-100 to-purple-100 opacity-50 blur-3xl"></div>
          
          <div class="relative z-10 px-8 py-8 border-b border-slate-100">
            <div class="flex items-center gap-3">
              <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-indigo-50 text-indigo-600">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 21V5a2 2 0 00-2-2H7a2 2 0 00-2 2v16m14 0h2m-2 0h-5m-9 0H3m2 0h5M9 7h1m-1 4h1m4-4h1m-1 4h1m-5 10v-5a1 1 0 011-1h2a1 1 0 011 1v5m-4 0h4"></path></svg>
              </div>
              <div>
                <h3 class="text-2xl font-extrabold text-slate-900">新建班级</h3>
                <p class="text-sm text-slate-500 mt-1">给你的新班级起个响亮的名字</p>
              </div>
            </div>
          </div>

          <div class="relative z-10 p-8 space-y-6 bg-slate-50/50">
            <div>
              <label class="mb-2 block text-sm font-semibold text-slate-700">班级名称 <span class="text-rose-500">*</span></label>
              <input
                v-model.trim="classForm.name"
                type="text"
                class="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 outline-none transition focus:border-indigo-500 focus:bg-white"
                placeholder="例如：2026春季火箭班 🚀"
              />
            </div>

            <div>
              <label class="mb-2 block text-sm font-semibold text-slate-700">班级说明</label>
              <textarea
                v-model.trim="classForm.description"
                rows="3"
                class="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 outline-none transition focus:border-indigo-500 focus:bg-white resize-none"
                placeholder="写点什么来描述这个班级吧..."
              />
            </div>

            <div v-if="classFormError" class="rounded-lg bg-rose-50 px-4 py-3 text-sm font-medium text-rose-600 flex items-center gap-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              {{ classFormError }}
            </div>
          </div>

          <div class="relative z-10 flex items-center justify-end gap-3 px-8 py-6 border-t border-slate-100 bg-white">
            <button
              type="button"
              @click="closeCreateClassModal"
              class="rounded-xl px-6 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-100"
            >
              取消
            </button>
            <button
              type="button"
              @click="createClass"
              :disabled="classSubmitting"
              class="rounded-xl bg-indigo-600 px-6 py-2.5 text-sm font-bold text-white shadow-md shadow-indigo-200 transition hover:bg-indigo-700 hover:shadow-lg disabled:opacity-70 disabled:cursor-not-allowed flex items-center gap-2"
            >
              <svg v-if="classSubmitting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              {{ classSubmitting ? '魔法生成中...' : '确认创建' }}
            </button>
          </div>
        </div>
      </div>
    </transition>

    <transition name="fade">
      <div v-if="showCreateStudentModal && activeClass" class="fixed inset-0 z-50 flex items-center justify-center p-2 sm:p-4">
        <!-- Backdrop -->
        <div class="absolute inset-0 bg-slate-900/40 backdrop-blur-sm" @click="closeCreateStudentModal"></div>
        
        <!-- Modal Content -->
        <div class="relative flex max-h-[calc(100vh-1rem)] w-full max-w-4xl flex-col overflow-hidden rounded-[2rem] bg-white shadow-2xl transform transition-all sm:max-h-[calc(100vh-2rem)]">
          <div class="absolute right-0 top-0 h-40 w-40 -translate-y-16 translate-x-16 rounded-full bg-gradient-to-br from-emerald-100 to-teal-100 opacity-50 blur-3xl"></div>
          
          <div class="relative z-10 border-b border-slate-100 px-5 py-5 sm:px-8 sm:py-8">
            <div class="flex items-center gap-3">
              <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-emerald-50 text-emerald-600">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M18 9v3m0 0v3m0-3h3m-3 0h-3m-2-5a4 4 0 11-8 0 4 4 0 018 0zM3 20a6 6 0 0112 0v1H3v-1z"></path></svg>
              </div>
              <div>
                <h3 class="text-2xl font-extrabold text-slate-900">招募新同学</h3>
                <p class="text-sm text-slate-500 mt-1">加入 <span class="font-bold text-slate-700">{{ activeClass.name }}</span></p>
              </div>
            </div>
          </div>

          <div class="relative z-10 min-h-0 flex-1 space-y-6 overflow-y-auto bg-slate-50/50 p-5 sm:p-8">
            <div class="inline-flex rounded-2xl border border-slate-200 bg-white p-1 shadow-sm">
              <button
                type="button"
                @click="studentMode = 'existing'"
                class="rounded-xl px-4 py-2 text-sm font-semibold transition"
                :class="studentMode === 'existing' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'"
              >
                选择已有学生
              </button>
              <button
                type="button"
                @click="studentMode = 'create'"
                class="rounded-xl px-4 py-2 text-sm font-semibold transition"
                :class="studentMode === 'create' ? 'bg-emerald-600 text-white shadow-sm' : 'text-slate-500 hover:text-slate-700'"
              >
                新建学生
              </button>
            </div>

            <div v-if="studentMode === 'existing'" class="space-y-5">
              <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
                <div class="relative w-full lg:max-w-md">
                  <input
                    v-model.trim="studentSearchKeyword"
                    type="text"
                    class="w-full rounded-xl border-2 border-slate-200 px-4 py-3 pl-11 text-slate-800 placeholder-slate-400 outline-none transition focus:border-emerald-500 focus:bg-white"
                    placeholder="搜索用户名、姓名或邮箱"
                  />
                  <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z"></path></svg>
                  </div>
                </div>

                <div class="flex flex-wrap items-center gap-3 text-sm">
                  <span class="rounded-full bg-white px-3 py-2 font-semibold text-slate-600 shadow-sm border border-slate-200">
                    已选 {{ selectedExistingStudentIds.length }} 人
                  </span>
                  <button
                    type="button"
                    @click="toggleSelectAllVisibleStudents"
                    :disabled="selectableVisibleStudentCandidates.length === 0"
                    class="rounded-xl border border-slate-200 bg-white px-4 py-2 font-semibold text-slate-600 transition hover:border-emerald-200 hover:text-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
                  >
                    {{ allVisibleSelectableStudentsSelected ? '取消全选' : '全选当前结果' }}
                  </button>
                </div>
              </div>

              <div v-if="studentCandidatesLoading" class="space-y-3">
                <div v-for="index in 5" :key="index" class="h-16 animate-pulse rounded-2xl bg-white/80 border border-slate-100"></div>
              </div>

              <div v-else-if="filteredStudentCandidates.length === 0" class="rounded-2xl border border-dashed border-slate-200 bg-white px-6 py-12 text-center">
                <div class="text-base font-semibold text-slate-800">没有可选学生</div>
                <div class="mt-2 text-sm text-slate-500">当前没有匹配的已注册学生，可切换到“新建学生”。</div>
              </div>

              <div v-else class="space-y-3 pr-1 sm:pr-2">
                <label
                  v-for="student in filteredStudentCandidates"
                  :key="student.id"
                  class="flex cursor-pointer items-center justify-between rounded-2xl border bg-white px-4 py-4 shadow-sm transition"
                  :class="student.already_in_class ? 'border-slate-100 opacity-75' : 'border-slate-100 hover:border-emerald-200 hover:shadow-md'"
                >
                  <div class="flex min-w-0 items-center gap-4">
                    <input
                      :checked="selectedExistingStudentIds.includes(student.id)"
                      :disabled="student.already_in_class"
                      type="checkbox"
                      class="h-4 w-4 rounded border-slate-300 text-emerald-600"
                      @change="toggleExistingStudentSelection(student.id)"
                    />
                    <div class="flex h-11 w-11 items-center justify-center rounded-full bg-gradient-to-br from-emerald-100 to-teal-100 text-sm font-bold text-emerald-700">
                      {{ (student.full_name || student.username).charAt(0).toUpperCase() }}
                    </div>
                    <div class="min-w-0">
                      <div class="flex flex-wrap items-center gap-2">
                        <span class="truncate text-sm font-bold text-slate-800">{{ student.full_name || student.username }}</span>
                        <span class="rounded-full bg-slate-100 px-2 py-0.5 text-[11px] font-semibold text-slate-500">{{ student.username }}</span>
                      </div>
                      <div class="mt-1 truncate text-xs text-slate-400">{{ student.email }}</div>
                    </div>
                  </div>

                  <span
                    class="ml-4 shrink-0 rounded-full px-3 py-1 text-xs font-bold"
                    :class="student.already_in_class ? 'bg-slate-100 text-slate-500' : 'bg-emerald-50 text-emerald-600'"
                  >
                    {{ student.already_in_class ? '已在班级' : '可加入' }}
                  </span>
                </label>
              </div>
            </div>

            <div v-else class="space-y-5">
              <div class="grid grid-cols-1 gap-5 md:grid-cols-2">
                <div>
                  <label class="mb-2 block text-sm font-semibold text-slate-700">姓名</label>
                  <input
                    v-model.trim="studentForm.full_name"
                    type="text"
                    class="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 outline-none transition focus:border-emerald-500 focus:bg-white"
                    placeholder="例如：李雷"
                  />
                </div>

                <div>
                  <label class="mb-2 block text-sm font-semibold text-slate-700">用户名 <span class="text-rose-500">*</span></label>
                  <input
                    v-model.trim="studentForm.username"
                    type="text"
                    class="w-full rounded-xl border-2 border-slate-200 px-4 py-3 text-slate-800 placeholder-slate-400 outline-none transition focus:border-emerald-500 focus:bg-white"
                    placeholder="登录账号"
                  />
                </div>
              </div>

              <div>
                <label class="mb-2 block text-sm font-semibold text-slate-700">邮箱 <span class="text-rose-500">*</span></label>
                <div class="relative">
                  <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                  </div>
                  <input
                    v-model.trim="studentForm.email"
                    type="email"
                    class="w-full rounded-xl border-2 border-slate-200 pl-11 pr-4 py-3 text-slate-800 placeholder-slate-400 outline-none transition focus:border-emerald-500 focus:bg-white"
                    placeholder="lilei@school.com"
                  />
                </div>
              </div>

              <div>
                <label class="mb-2 block text-sm font-semibold text-slate-700">初始密码 <span class="text-rose-500">*</span></label>
                <div class="relative">
                  <div class="absolute inset-y-0 left-0 pl-3.5 flex items-center pointer-events-none text-slate-400">
                    <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 15v2m-6 4h12a2 2 0 002-2v-6a2 2 0 00-2-2H6a2 2 0 00-2 2v6a2 2 0 002 2zm10-10V7a4 4 0 00-8 0v4h8z"></path></svg>
                  </div>
                  <input
                    v-model="studentForm.password"
                    type="text"
                    class="w-full rounded-xl border-2 border-slate-200 pl-11 pr-4 py-3 text-slate-800 placeholder-slate-400 outline-none transition focus:border-emerald-500 focus:bg-white"
                    placeholder="至少 6 位密码"
                  />
                </div>
              </div>
            </div>

            <div v-if="studentFormError" class="rounded-lg bg-rose-50 px-4 py-3 text-sm font-medium text-rose-600 flex items-center gap-2 mt-2">
              <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"></path></svg>
              {{ studentFormError }}
            </div>
          </div>

          <div class="relative z-10 flex flex-col-reverse gap-3 border-t border-slate-100 bg-white px-5 py-4 sm:flex-row sm:items-center sm:justify-end sm:px-8 sm:py-6">
            <button
              type="button"
              @click="closeCreateStudentModal"
              class="w-full rounded-xl px-6 py-2.5 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 sm:w-auto"
            >
              取消
            </button>
            <button
              type="button"
              @click="submitStudentAction"
              :disabled="studentSubmitting"
              class="flex w-full items-center justify-center gap-2 rounded-xl bg-emerald-600 px-6 py-2.5 text-sm font-bold text-white shadow-md shadow-emerald-200 transition hover:bg-emerald-700 hover:shadow-lg disabled:cursor-not-allowed disabled:opacity-70 sm:w-auto"
            >
              <svg v-if="studentSubmitting" class="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24"><circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle><path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path></svg>
              {{ studentSubmitting ? '添加中...' : (studentMode === 'existing' ? '加入班级' : '确认创建') }}
            </button>
          </div>
        </div>
      </div>
    </transition>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { teacherClassAPI } from '@/api';
import { register } from '@/api/auth';
import dialogService from '@/services/dialogService';
import notificationService from '@/services/notificationService';
import {
  syncMyClassesCache,
  type MyClassStudentRecord,
  type TeacherClassRecord,
} from '@/services/myClassService';

const props = withDefaults(defineProps<{
  hideHeader?: boolean;
}>(), {
  hideHeader: false
});

const authStore = useAuthStore();
const teacherId = computed(() => authStore.user?.id ?? null);

const loading = ref(false);
const classes = ref<TeacherClassRecord[]>([]);

const showCreateClassModal = ref(false);
const classSubmitting = ref(false);
const classFormError = ref('');
const classForm = reactive({
  name: '',
  description: '',
});

const showCreateStudentModal = ref(false);
const studentSubmitting = ref(false);
const studentFormError = ref('');
const activeClass = ref<TeacherClassRecord | null>(null);
const studentMode = ref<'existing' | 'create'>('existing');
const studentSearchKeyword = ref('');
const studentCandidatesLoading = ref(false);
const studentCandidates = ref<Array<MyClassStudentRecord & { already_in_class?: boolean }>>([]);
const selectedExistingStudentIds = ref<number[]>([]);
const studentForm = reactive({
  username: '',
  email: '',
  password: '',
  full_name: '',
});

const uniqueStudentCount = computed(() => {
  const studentIds = new Set<number>();
  classes.value.forEach((teacherClass) => {
    (teacherClass.students || []).forEach((student) => studentIds.add(student.id));
  });
  return studentIds.size;
});

const filteredStudentCandidates = computed(() => {
  const keyword = studentSearchKeyword.value.trim().toLowerCase();
  if (!keyword) {
    return studentCandidates.value;
  }

  return studentCandidates.value.filter(student =>
    [student.username, student.email, student.full_name].some(field =>
      String(field || '').toLowerCase().includes(keyword)
    )
  );
});

const selectableVisibleStudentCandidates = computed(() =>
  filteredStudentCandidates.value.filter(student => !student.already_in_class)
);

const allVisibleSelectableStudentsSelected = computed(() => {
  const selectableIds = selectableVisibleStudentCandidates.value.map(student => student.id);
  return selectableIds.length > 0 && selectableIds.every(id => selectedExistingStudentIds.value.includes(id));
});

async function fetchClasses() {
  loading.value = true;
  try {
    const response = await teacherClassAPI.getClasses() as { classes?: TeacherClassRecord[] };
    classes.value = response.classes || [];
    syncMyClassesCache(teacherId.value, classes.value);
  } catch (error) {
    console.error('获取班级列表失败:', error);
    notificationService.error('获取失败', '无法加载我的班级数据');
    classes.value = [];
    syncMyClassesCache(teacherId.value, []);
  } finally {
    loading.value = false;
  }
}

function resetClassForm() {
  classForm.name = '';
  classForm.description = '';
  classFormError.value = '';
}

function openCreateClassModal() {
  resetClassForm();
  showCreateClassModal.value = true;
}

function closeCreateClassModal() {
  showCreateClassModal.value = false;
  resetClassForm();
}

async function createClass() {
  if (!classForm.name) {
    classFormError.value = '请填写班级名称';
    return;
  }

  classSubmitting.value = true;
  classFormError.value = '';

  try {
    await teacherClassAPI.createClass({
      name: classForm.name,
      description: classForm.description || undefined,
    });
    closeCreateClassModal();
    await fetchClasses();
    notificationService.success('创建成功', `班级 ${classForm.name} 已创建`);
  } catch (error: any) {
    console.error('创建班级失败:', error);
    classFormError.value = error?.error || error?.message || '创建班级失败，请稍后重试';
  } finally {
    classSubmitting.value = false;
  }
}

function resetStudentForm() {
  studentForm.username = '';
  studentForm.email = '';
  studentForm.password = '';
  studentForm.full_name = '';
  studentMode.value = 'existing';
  studentSearchKeyword.value = '';
  studentCandidates.value = [];
  selectedExistingStudentIds.value = [];
  studentFormError.value = '';
}

async function fetchStudentCandidates() {
  if (!activeClass.value) {
    studentCandidates.value = [];
    return;
  }

  studentCandidatesLoading.value = true;
  try {
    const response = await teacherClassAPI.getAvailableStudents(activeClass.value.id) as {
      students?: Array<MyClassStudentRecord & { already_in_class?: boolean }>;
    };
    studentCandidates.value = response.students || [];
  } catch (error) {
    console.error('获取已注册学生失败:', error);
    studentCandidates.value = [];
    studentFormError.value = '无法加载已注册学生列表，请稍后重试';
  } finally {
    studentCandidatesLoading.value = false;
  }
}

async function openCreateStudentModal(teacherClass: TeacherClassRecord) {
  activeClass.value = teacherClass;
  resetStudentForm();
  showCreateStudentModal.value = true;
  await fetchStudentCandidates();
}

function closeCreateStudentModal() {
  showCreateStudentModal.value = false;
  activeClass.value = null;
  resetStudentForm();
}

async function createStudent() {
  if (!activeClass.value) {
    studentFormError.value = '未选择目标班级';
    return;
  }

  if (!studentForm.username || !studentForm.email || !studentForm.password) {
    studentFormError.value = '请填写用户名、邮箱和初始密码';
    return;
  }

  if (studentForm.password.length < 6) {
    studentFormError.value = '初始密码至少 6 位';
    return;
  }

  studentSubmitting.value = true;
  studentFormError.value = '';

  try {
    const displayName = studentForm.full_name || studentForm.username;
    const className = activeClass.value.name;
    const response = await register({
      username: studentForm.username,
      email: studentForm.email,
      password: studentForm.password,
      full_name: studentForm.full_name,
      role: 'student',
    }) as { user?: MyClassStudentRecord };

    const user = response?.user;
    if (!user?.id) {
      throw new Error('注册接口未返回学生信息');
    }

    await teacherClassAPI.addStudents(activeClass.value.id, [user.id]);
    closeCreateStudentModal();
    await fetchClasses();
    notificationService.success('添加成功', `学生 ${displayName} 已加入 ${className}`);
  } catch (error: any) {
    console.error('创建班级学生失败:', error);
    studentFormError.value = error?.error || error?.message || '创建学生失败，请稍后重试';
  } finally {
    studentSubmitting.value = false;
  }
}

function toggleExistingStudentSelection(studentId: number) {
  const index = selectedExistingStudentIds.value.indexOf(studentId);
  if (index >= 0) {
    selectedExistingStudentIds.value.splice(index, 1);
    return;
  }
  selectedExistingStudentIds.value.push(studentId);
}

function toggleSelectAllVisibleStudents() {
  const visibleIds = selectableVisibleStudentCandidates.value.map(student => student.id);
  if (visibleIds.length === 0) {
    return;
  }

  if (allVisibleSelectableStudentsSelected.value) {
    selectedExistingStudentIds.value = selectedExistingStudentIds.value.filter(id => !visibleIds.includes(id));
    return;
  }

  const nextIds = new Set(selectedExistingStudentIds.value);
  visibleIds.forEach(id => nextIds.add(id));
  selectedExistingStudentIds.value = Array.from(nextIds);
}

async function addExistingStudentsToClass() {
  if (!activeClass.value) {
    studentFormError.value = '未选择目标班级';
    return;
  }

  if (selectedExistingStudentIds.value.length === 0) {
    studentFormError.value = '请至少选择一名已注册学生';
    return;
  }

  studentSubmitting.value = true;
  studentFormError.value = '';

  try {
    await teacherClassAPI.addStudents(activeClass.value.id, selectedExistingStudentIds.value);
    const className = activeClass.value.name;
    const addedCount = selectedExistingStudentIds.value.length;
    closeCreateStudentModal();
    await fetchClasses();
    notificationService.success('添加成功', `已将 ${addedCount} 名学生加入 ${className}`);
  } catch (error: any) {
    console.error('添加已注册学生失败:', error);
    studentFormError.value = error?.error || error?.message || '添加学生失败，请稍后重试';
  } finally {
    studentSubmitting.value = false;
  }
}

async function submitStudentAction() {
  if (studentMode.value === 'existing') {
    await addExistingStudentsToClass();
    return;
  }

  await createStudent();
}

async function confirmDeleteClass(teacherClass: TeacherClassRecord) {
  const confirmed = await dialogService.warning({
    title: '删除班级',
    message: `确定删除班级“${teacherClass.name}”吗？班级成员关系会被清空，但不会删除学生账号。`,
    confirmText: '删除',
    cancelText: '取消',
  });

  if (!confirmed) {
    return;
  }

  try {
    await teacherClassAPI.deleteClass(teacherClass.id);
    await fetchClasses();
    notificationService.success('删除成功', `班级 ${teacherClass.name} 已删除`);
  } catch (error) {
    console.error('删除班级失败:', error);
    notificationService.error('删除失败', '删除班级失败，请稍后重试');
  }
}

async function confirmRemoveStudent(teacherClass: TeacherClassRecord, student: MyClassStudentRecord) {
  const confirmed = await dialogService.warning({
    title: '移出班级',
    message: `确定将 ${student.full_name || student.username} 从“${teacherClass.name}”中移除吗？这不会删除该学生账号。`,
    confirmText: '移出',
    cancelText: '取消',
  });

  if (!confirmed) {
    return;
  }

  try {
    await teacherClassAPI.removeStudent(teacherClass.id, student.id);
    await fetchClasses();
    notificationService.success('移除成功', `${student.full_name || student.username} 已从 ${teacherClass.name} 移除`);
  } catch (error) {
    console.error('移出班级学生失败:', error);
    notificationService.error('移除失败', '移出学生失败，请稍后重试');
  }
}

function formatDate(value?: string) {
  if (!value) {
    return '未记录';
  }

  return new Date(value).toLocaleString('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  });
}

onMounted(() => {
  fetchClasses();
});
</script>

<style scoped>
/* 滚动条美化 */
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

/* Modal 动画 */
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
</style>
