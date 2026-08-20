<template>
  <div class="bg-white p-6 rounded-lg shadow-md border border-gray-200">
    <div class="flex justify-between items-center mb-4">
      <h3 class="text-lg font-semibold">AI学习建议</h3>
      <button 
        @click="generateAnalysis" 
        class="px-3 py-1 text-sm rounded-md bg-blue-100 text-blue-800 hover:bg-blue-200 flex items-center"
        :disabled="loading"
      >
        <svg v-if="loading" class="animate-spin -ml-1 mr-2 h-4 w-4 text-blue-800" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle class="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" stroke-width="4"></circle>
          <path class="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
        </svg>
        <span>{{ loading ? '生成中...' : '刷新建议' }}</span>
      </button>
    </div>
    
    <div v-if="!hasVisibleAnalysis && !loading" class="text-center py-8">
      <svg xmlns="http://www.w3.org/2000/svg" class="h-12 w-12 mx-auto text-gray-400 mb-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9.663 17h4.673M12 3v1m6.364 1.636l-.707.707M21 12h-1M4 12H3m3.343-5.657l-.707-.707m2.828 9.9a5 5 0 117.072 0l-.548.547A3.374 3.374 0 0014 18.469V19a2 2 0 11-4 0v-.531c0-.895-.356-1.754-.988-2.386l-.548-.547z" />
      </svg>
      <h3 class="text-lg font-medium text-gray-900 mb-2">暂无AI分析</h3>
      <p class="text-gray-500 mb-2">{{ emptyMessage }}</p>
      <p v-if="errorMessage" class="text-sm text-red-600">{{ errorMessage }}</p>
    </div>
    
    <div v-else-if="loading" class="flex flex-col items-center justify-center py-8">
      <div class="animate-pulse flex space-x-4 w-full mb-4">
        <div class="flex-1 space-y-4 py-1">
          <div class="h-4 bg-gray-200 rounded w-3/4"></div>
          <div class="space-y-2">
            <div class="h-4 bg-gray-200 rounded"></div>
            <div class="h-4 bg-gray-200 rounded w-5/6"></div>
            <div class="h-4 bg-gray-200 rounded w-4/6"></div>
          </div>
        </div>
      </div>
      <p class="text-sm text-gray-500">AI正在分析您的学习数据，请稍候...</p>
    </div>
    
    <div v-else-if="analysis">
      <!-- 学习强项 -->
      <div class="mb-4">
        <h4 class="text-md font-medium text-green-700 mb-2 flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          学习强项
        </h4>
        <ul class="list-disc list-inside text-sm text-gray-700 pl-2">
          <li v-for="(strength, index) in analysis.strengths" :key="`strength-${index}`" class="mb-1">
            {{ strength }}
          </li>
        </ul>
      </div>
      
      <!-- 改进建议 -->
      <div class="mb-4">
        <h4 class="text-md font-medium text-yellow-700 mb-2 flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          改进建议
        </h4>
        <ul class="list-disc list-inside text-sm text-gray-700 pl-2">
          <li v-for="(improvement, index) in analysis.improvements" :key="`improvement-${index}`" class="mb-1">
            {{ improvement }}
          </li>
        </ul>
      </div>
      
      <!-- 学习建议 -->
      <div>
        <h4 class="text-md font-medium text-blue-700 mb-2 flex items-center">
          <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          学习建议
        </h4>
        <ul class="list-disc list-inside text-sm text-gray-700 pl-2">
          <li v-for="(suggestion, index) in analysis.suggestions" :key="`suggestion-${index}`" class="mb-1">
            {{ suggestion }}
          </li>
        </ul>
      </div>
      
      <div class="mt-4 pt-4 border-t border-gray-200 text-xs text-gray-500">
        分析生成时间: {{ new Date(analysis.timestamp).toLocaleString() }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue';
import { analyticsAPI } from '@/api';

const props = defineProps({
  userId: {
    type: [Number, String],
    default: null
  },
  courseId: {
    type: [Number, String],
    default: null
  }
});

interface AIAnalysis {
  strengths: string[];
  improvements: string[];
  suggestions: string[];
  timestamp: string;
}

const loading = ref(false);
const analysis = ref<AIAnalysis | null>(null);
const errorMessage = ref('');

const hasVisibleAnalysis = computed(() => {
  if (!analysis.value) {
    return false;
  }
  return (
    analysis.value.strengths.length > 0 ||
    analysis.value.improvements.length > 0 ||
    analysis.value.suggestions.length > 0
  );
});

const emptyMessage = computed(() => {
  if (errorMessage.value) {
    return '学习建议加载失败，当前未展示建议内容。';
  }
  return '当前学习数据不足，暂时无法生成个性化建议。';
});

// 生成AI分析建议
async function generateAnalysis() {
  try {
    loading.value = true;
    errorMessage.value = '';
    
    // 构建请求参数
    const params: {studentId?: number | string, courseId?: number | string} = {};
    if (props.userId) params.studentId = props.userId;
    if (props.courseId) params.courseId = props.courseId;
    
    console.log('发送AI分析请求:', params);
    
    if (!params.studentId) {
      analysis.value = null;
      return;
    }

    const response = await analyticsAPI.getAIAnalysis(params) as any;

    if (response && typeof response === 'object') {
      analysis.value = {
        strengths: Array.isArray(response.strengths) ? response.strengths : [],
        improvements: Array.isArray(response.improvements) ? response.improvements : [],
        suggestions: Array.isArray(response.suggestions) ? response.suggestions : [],
        timestamp: response.timestamp || new Date().toISOString()
      };
      console.log('获取AI分析成功:', response);
    } else {
      analysis.value = null;
    }
  } catch (error: any) {
    console.error('获取AI分析建议失败:', error);
    errorMessage.value = error?.response?.data?.error || '学习建议接口暂时不可用';
    analysis.value = null;
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void generateAnalysis();
});

watch(
  () => [props.userId, props.courseId],
  () => {
    void generateAnalysis();
  }
);
</script>
