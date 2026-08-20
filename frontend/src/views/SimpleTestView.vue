<template>
  <div class="simple-test">
    <div class="container mx-auto px-4 py-8">
      <h1 class="text-3xl font-bold mb-8 text-center">AI鍔╂墜鍔熻兘娴嬭瘯</h1>
      
      <div class="bg-white rounded-lg shadow-md p-6">
        <!-- API鐘舵€佹祴璇?-->
        <div class="mb-6 p-4 border rounded-lg">
          <h3 class="text-lg font-semibold mb-3">1. API鐘舵€佹鏌?/h3>
          <button 
            @click="checkAPIStatus" 
            :disabled="loading"
            class="bg-blue-600 text-white px-4 py-2 rounded hover:bg-blue-700 disabled:bg-gray-400"
          >
            {{ loading ? '妫€鏌ヤ腑...' : '妫€鏌PI鐘舵€? }}
          </button>
          <div v-if="apiStatus" class="mt-3 p-3 bg-gray-100 rounded text-sm">
            <pre>{{ JSON.stringify(apiStatus, null, 2) }}</pre>
          </div>
        </div>

        <!-- 璇剧▼鍒楄〃娴嬭瘯 -->
        <div class="mb-6 p-4 border rounded-lg">
          <h3 class="text-lg font-semibold mb-3">2. 璇剧▼鍒楄〃鑾峰彇</h3>
          <button 
            @click="fetchCourses" 
            :disabled="loading"
            class="bg-green-600 text-white px-4 py-2 rounded hover:bg-green-700 disabled:bg-gray-400"
          >
            {{ loading ? '鑾峰彇涓?..' : '鑾峰彇璇剧▼鍒楄〃' }}
          </button>
          <div v-if="courses.length > 0" class="mt-3 p-3 bg-green-50 rounded">
            <p class="font-medium text-green-800">鎵惧埌 {{ courses.length }} 涓绋?</p>
            <ul class="mt-2 space-y-1">
              <li v-for="course in courses" :key="course.id" class="text-sm">
                <span class="font-medium">ID: {{ course.id }}</span> - {{ course.name }}
              </li>
            </ul>
          </div>
          <div v-else-if="coursesError" class="mt-3 p-3 bg-red-50 rounded text-red-800">
            {{ coursesError }}
          </div>
        </div>

        <!-- 鑱婂ぉ娴嬭瘯 -->
        <div class="mb-6 p-4 border rounded-lg">
          <h3 class="text-lg font-semibold mb-3">3. 鑱婂ぉ鍔熻兘娴嬭瘯</h3>
          
          <div class="grid grid-cols-1 md:grid-cols-2 gap-4 mb-4">
            <div>
              <label class="block text-sm font-medium mb-1">鑱婂ぉ妯″紡:</label>
              <select v-model="chatMode" class="w-full p-2 border rounded">
                <option value="general">鏅€欰I闂瓟</option>
                <option value="rag">鐭ヨ瘑搴撳寮?/option>
              </select>
            </div>
            
            <div v-if="chatMode === 'rag'">
              <label class="block text-sm font-medium mb-1">閫夋嫨璇剧▼:</label>
              <select v-model="selectedCourseId" class="w-full p-2 border rounded">
                <option value="">璇烽€夋嫨璇剧▼</option>
                <option v-for="course in courses" :key="course.id" :value="course.id">
                  {{ course.name }} (ID: {{ course.id }})
                </option>
              </select>
            </div>
          </div>
          
          <div class="mb-4">
            <label class="block text-sm font-medium mb-1">杈撳叆闂:</label>
            <input 
              v-model="testMessage" 
              placeholder="杈撳叆娴嬭瘯闂..." 
              class="w-full p-2 border rounded"
            />
          </div>
          
          <button 
            @click="testChat" 
            :disabled="loading || !testMessage.trim() || (chatMode === 'rag' && !selectedCourseId)"
            class="bg-purple-600 text-white px-4 py-2 rounded hover:bg-purple-700 disabled:bg-gray-400"
          >
            {{ loading ? '鍙戦€佷腑...' : '鍙戦€佹祴璇曟秷鎭? }}
          </button>
          
          <div v-if="chatResponse" class="mt-3 p-3 bg-gray-100 rounded">
            <h4 class="font-medium mb-2">鍝嶅簲缁撴灉:</h4>
            <pre class="text-sm">{{ JSON.stringify(chatResponse, null, 2) }}</pre>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { ragAiAPI, courseAPI } from '../api'

interface CourseItem {
  id: number | string
  name: string
}

interface TestResult {
  success: boolean
  data?: unknown
  error?: string
  details?: unknown
}

interface ChatParams {
  message: string
  stream: boolean
  course_id?: string | number
  use_rag?: boolean
}

const loading = ref(false)
const apiStatus = ref<TestResult | null>(null)
const courses = ref<CourseItem[]>([])
const coursesError = ref<string | null>(null)
const chatMode = ref<'general' | 'rag'>('general')
const selectedCourseId = ref<string | number>('')
const testMessage = ref('你好，请介绍一下你自己')
const chatResponse = ref<TestResult | null>(null)

const getErrorInfo = (error: unknown) => {
  const errorObj = error as { message?: string; response?: { data?: unknown } }
  return {
    message: errorObj?.message || '未知错误',
    details: errorObj?.response?.data
  }
}

const checkAPIStatus = async () => {
  loading.value = true
  try {
    const response = await ragAiAPI.getStatus()
    const responseData = (response as any)?.data ?? response
    apiStatus.value = {
      success: true,
      data: responseData
    }
  } catch (error) {
    const errorInfo = getErrorInfo(error)
    apiStatus.value = {
      success: false,
      error: errorInfo.message,
      details: errorInfo.details
    }
  } finally {
    loading.value = false
  }
}

const fetchCourses = async () => {
  loading.value = true
  coursesError.value = null
  try {
    const response = await courseAPI.getCourses()
    const responseData = (response as any)?.data ?? response
    if (Array.isArray(responseData?.courses)) {
      courses.value = responseData.courses
    } else if (Array.isArray(responseData)) {
      courses.value = responseData
    } else {
      courses.value = []
    }
  } catch (error) {
    const errorInfo = getErrorInfo(error)
    coursesError.value = `获取课程失败: ${errorInfo.message}`
    console.error('获取课程失败:', error)
  } finally {
    loading.value = false
  }
}

const testChat = async () => {
  loading.value = true
  chatResponse.value = null

  try {
    const params: ChatParams = {
      message: testMessage.value,
      stream: false
    }

    if (chatMode.value === 'rag' && selectedCourseId.value) {
      params.course_id = selectedCourseId.value
      params.use_rag = true
    } else {
      params.use_rag = false
    }

    const response = await ragAiAPI.chat(params)
    const responseData = (response as any)?.data ?? response

    chatResponse.value = {
      success: true,
      data: responseData
    }
  } catch (error) {
    const errorInfo = getErrorInfo(error)
    chatResponse.value = {
      success: false,
      error: errorInfo.message,
      details: errorInfo.details
    }
    console.error('聊天测试失败:', error)
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.simple-test {
  min-height: 100vh;
  background-color: #f8fafc;
}
</style> 
