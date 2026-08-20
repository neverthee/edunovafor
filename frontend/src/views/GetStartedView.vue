<template>
  <div class="min-h-screen bg-slate-50 selection:bg-primary-100 selection:text-primary-900">
    <!-- 装饰背景 -->
    <div class="fixed inset-0 -z-10 overflow-hidden">
      <div class="absolute -left-[10%] -top-[10%] h-[40%] w-[40%] rounded-full bg-primary-100/50 blur-[120px]"></div>
      <div class="absolute -right-[10%] bottom-[10%] h-[35%] w-[35%] rounded-full bg-blue-100/40 blur-[100px]"></div>
      <div class="absolute inset-0 bg-[url('https://www.transparenttextures.com/patterns/cubes.png')] opacity-[0.03]"></div>
    </div>

    <main class="relative mx-auto max-w-7xl px-4 py-8 sm:px-6 lg:px-8 lg:py-10">
      <!-- 顶部徽标 -->
      <div class="flex flex-col items-center animate-fade-in">
        <div class="inline-flex items-center gap-2.5 rounded-full border border-primary-100 bg-white/60 px-4 py-1.5 text-sm font-semibold text-primary-700 shadow-sm backdrop-blur-md transition-transform hover:scale-105">
          <img src="@/assets/images/atom.png" alt="Atom Icon" class="h-4 w-4 animate-pulse" />
          <span>开始体验易度新星 EduNova 智能教学实训系统</span>
        </div>
        
        <h1 class="mt-5 text-center text-3xl font-extrabold tracking-tight text-slate-900 sm:text-5xl">
          <span class="block">开启您的</span>
          <span class="mt-1.5 block bg-gradient-to-r from-primary-600 to-blue-500 bg-clip-text text-transparent">数字化教学旅程</span>
        </h1>
        
        <p class="mx-auto mt-4 max-w-2xl text-center text-base leading-relaxed text-slate-600 sm:text-lg">
          易度新星 EduNova 为您提供全方位的智能教学解决方案，通过 RAG 增强与 AI 驱动，让知识传递更高效、更智能。
        </p>
      </div>

      <!-- 入口选项 -->
      <div class="mt-10 grid gap-6 lg:grid-cols-2 lg:items-stretch animate-slide-up">
        <!-- 示例账号卡片 -->
        <div class="group relative flex flex-col overflow-hidden rounded-[2.5rem] border border-slate-200 bg-white p-1 shadow-2xl shadow-slate-200/50 transition-all hover:border-primary-200">
          <div class="flex flex-1 flex-col p-6 sm:p-8">
            <div class="flex items-start justify-between">
              <div>
                <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-50 text-primary-600 ring-1 ring-primary-100 shadow-inner">
                  <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                    <path stroke-linecap="round" stroke-linejoin="round" d="M15 19.128a9.38 9.38 0 0 0 2.625.372 9.337 9.337 0 0 0 4.121-.952 4.125 4.125 0 0 0-7.533-2.493M15 19.128v-.003c0-1.113-.285-2.16-.786-3.07M15 19.128v.106A12.318 12.318 0 0 1 8.624 21c-2.331 0-4.512-.645-6.374-1.766l-.001-.109a6.375 6.375 0 0 1 11.964-3.07M12 6.375a3.375 3.375 0 1 1-6.75 0 3.375 3.375 0 0 1 6.75 0Zm8.25 2.25a2.625 2.625 0 1 1-5.25 0 2.625 2.625 0 0 1 5.25 0Z" />
                  </svg>
                </div>
                <h2 class="mt-4 text-2xl font-bold text-slate-900">示例账号登录</h2>
                <p class="mt-1.5 text-sm text-slate-500">快速进入系统，体验教师与学生的核心功能</p>
              </div>
              <div class="hidden sm:block">
                <span class="inline-flex items-center rounded-full bg-primary-50 px-2.5 py-0.5 text-xs font-semibold text-primary-700">推荐体验</span>
              </div>
            </div>

            <div class="mt-6 grid gap-3 sm:grid-cols-3">
              <button
                v-for="account in demoAccounts"
                :key="account.role"
                type="button"
                :disabled="authStore.isLoading"
                class="relative flex flex-col overflow-hidden rounded-2xl border border-slate-100 bg-slate-50/50 p-4 text-left transition-all hover:-translate-y-1 hover:border-primary-200 hover:bg-white hover:shadow-xl hover:shadow-primary-100/50 disabled:cursor-not-allowed disabled:opacity-60"
                @click="loginWithDemo(account)"
              >
                <div class="text-[10px] font-bold uppercase tracking-widest text-slate-400">
                  {{ account.role }}
                </div>
                <div class="mt-1 text-base font-bold text-slate-900">
                  {{ account.label }}
                </div>
                
                <div class="mt-auto pt-4">
                  <div class="flex items-center gap-1.5 text-sm font-semibold text-primary-600">
                    <span>{{ loadingRole === account.role ? '进入中' : '进入' }}</span>
                    <svg v-if="loadingRole === account.role" class="h-3.5 w-3.5 animate-spin" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                      <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
                      <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                    <svg v-else xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                      <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
                    </svg>
                  </div>
                </div>
              </button>
            </div>

            <div v-if="authStore.error" class="mt-4 rounded-xl border border-red-100 bg-red-50 p-4 text-sm text-red-600 flex items-center gap-3">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 flex-shrink-0" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M12 9v3.75m9-.75a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9 3.75h.008v.008H12v-.008Z" />
              </svg>
              {{ authStore.error }}
            </div>

            <div class="mt-5 flex items-center gap-2 text-xs text-slate-400">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="m11.25 11.25.041-.02a.75.75 0 0 1 1.063.852l-.708 2.836a.75.75 0 0 0 1.063.853l.041-.021M21 12a9 9 0 1 1-18 0 9 9 0 0 1 18 0Zm-9-3.75h.008v.008H12V8.25Z" />
              </svg>
              <span>账号：admin, teacher, student / 密码：同账号+123</span>
            </div>
          </div>
        </div>

        <!-- 自由登录卡片 -->
        <router-link
          to="/login"
          class="group relative flex flex-col overflow-hidden rounded-[2.5rem] border border-slate-200 bg-white p-1 shadow-2xl shadow-slate-200/50 transition-all hover:border-primary-200"
        >
          <!-- 背景装饰 -->
          <div class="absolute inset-0 bg-[radial-gradient(circle_at_top_right,_rgba(59,130,246,0.08),_transparent_55%)]"></div>
          <div class="absolute bottom-0 right-0 h-64 w-64 translate-x-20 translate-y-20 rounded-full bg-primary-100/60 blur-[100px]"></div>
          
          <div class="relative flex flex-1 flex-col p-6 sm:p-8">
            <div class="flex h-12 w-12 items-center justify-center rounded-2xl bg-primary-50 text-primary-600 ring-1 ring-primary-100 shadow-inner">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-6 w-6" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
                <path stroke-linecap="round" stroke-linejoin="round" d="M15.75 9V5.25A2.25 2.25 0 0 0 13.5 3h-7.5a2.25 2.25 0 0 0-2.25 2.25v13.5A2.25 2.25 0 0 0 6 21h7.5a2.25 2.25 0 0 0 2.25-2.25V15m3 0 3-3m0 0-3-3m3 3H9" />
              </svg>
            </div>
            
            <h2 class="mt-4 text-2xl font-bold text-slate-900">自由登录 / 注册</h2>
            <p class="mt-1.5 text-sm text-slate-500">
              使用您的个人账号登录，或者立即创建一个新账号来开启个性化的教学体验。
            </p>
            
            <div class="mt-7 inline-flex items-center gap-1.5 text-sm font-semibold text-primary-600 transition-all group-hover:gap-2.5 group-hover:text-primary-500">
              <span>进入登录页面</span>
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 transition-transform group-hover:translate-x-0.5" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5">
                <path stroke-linecap="round" stroke-linejoin="round" d="m8.25 4.5 7.5 7.5-7.5 7.5" />
              </svg>
            </div>
            
            <div class="mt-auto pt-10 flex items-center justify-between border-t border-slate-100">
              <div class="flex -space-x-2 overflow-hidden">
                <div v-for="i in 3" :key="i" class="inline-block flex h-8 w-8 items-center justify-center rounded-full bg-slate-100 ring-2 ring-white">
                  <span class="text-[10px] font-bold text-slate-500">{{ ['AI', 'KB', 'LP'][i-1] }}</span>
                </div>
              </div>
              <p class="text-sm text-slate-400">已有 2,000+ 师生加入</p>
            </div>
          </div>
        </router-link>
      </div>
      
      <!-- 页脚或辅助链接 -->
      <footer class="mt-10 text-center animate-fade-in delay-500">
        <p class="text-sm text-slate-400">
          &copy; 2026 易度新星 EduNova 智能教学实训系统. 保留所有权利。
        </p>
      </footer>
    </main>
  </div>
</template>


<script setup lang="ts">
import { onMounted, ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

type DemoRole = 'teacher' | 'student' | 'admin'

interface DemoAccount {
  role: DemoRole
  label: string
  username: string
  password: string
}

const router = useRouter()
const authStore = useAuthStore()
const loadingRole = ref<DemoRole | null>(null)

const demoAccounts: DemoAccount[] = [
  { role: 'teacher', label: '教师', username: 'teacher', password: 'teacher123' },
  { role: 'student', label: '学生', username: 'student', password: 'student123' },
  { role: 'admin', label: '管理员', username: 'admin', password: 'admin123' }
]

function getDashboardRoute() {
  const role = authStore.user?.role
  if (role === 'admin') return '/admin'
  if (role === 'teacher') return '/teacher'
  if (role === 'student') return '/student'
  return '/dashboard'
}

async function loginWithDemo(account: DemoAccount) {
  loadingRole.value = account.role
  authStore.clearError()

  try {
    await authStore.loginUser(account.username, account.password)
    router.push(getDashboardRoute())
  } catch (error) {
    console.error(`示例账号 ${account.role} 登录失败:`, error)
  } finally {
    loadingRole.value = null
  }
}

onMounted(() => {
  authStore.clearError()
  if (authStore.isAuthenticated) {
    router.replace(getDashboardRoute())
  }
})
</script>
