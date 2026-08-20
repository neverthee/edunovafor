<template>
  <div class="learning-analytics">
    <h2 class="text-2xl font-bold mb-6">学习分析</h2>
    
    <!-- 加载状态 -->
    <div v-if="loading" class="flex justify-center items-center py-20">
      <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
      <span class="ml-3 text-gray-600">加载中...</span>
    </div>
    
    <div v-else>
      <div v-if="errorMessage" class="mb-6 rounded-lg border border-red-200 bg-red-50 px-4 py-3 text-sm text-red-700">
        {{ errorMessage }}
      </div>

      <div class="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
        <!-- 学习进度 -->
        <div class="bg-white p-6 rounded-lg shadow-md border border-gray-200">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold">整体学习进度</h3>
            <span class="text-2xl font-bold text-blue-600">{{ overallProgress }}%</span>
          </div>
          <div class="w-full bg-gray-200 rounded-full h-3 mb-2">
            <div class="bg-blue-600 h-3 rounded-full" :style="`width: ${overallProgress}%`"></div>
          </div>
          <div class="flex justify-between text-sm text-gray-500">
            <span>开始</span>
            <span>完成</span>
          </div>
        </div>
        
        <!-- 学习时间 -->
        <div class="bg-white p-6 rounded-lg shadow-md border border-gray-200">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold">本周学习时间</h3>
            <span class="text-2xl font-bold text-green-600">{{ weeklyLearningTime }}小时</span>
          </div>
          <div class="flex items-center">
            <span class="text-sm text-gray-500 mr-2">上周：</span>
            <div class="w-full bg-gray-200 rounded-full h-2">
              <div class="bg-green-600 h-2 rounded-full" :style="`width: ${(previousWeekTime / 10) * 100}%`"></div>
            </div>
            <span class="text-sm text-gray-500 ml-2">{{ previousWeekTime }}小时</span>
          </div>
        </div>
        
        <!-- 完成课程 -->
        <div class="bg-white p-6 rounded-lg shadow-md border border-gray-200">
          <div class="flex justify-between items-center mb-4">
            <h3 class="text-lg font-semibold">课程完成情况</h3>
          </div>
          <CoursePieChart 
            :completed="completedCourses" 
            :in-progress="inProgressCourses" 
            :not-started="notStartedCourses" 
          />
        </div>
      </div>
      
      <!-- 学习趋势图 -->
      <div class="bg-white p-6 rounded-lg shadow-md border border-gray-200 mb-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">学习趋势</h3>
          <div class="flex items-center">
            <button 
              v-for="period in trendPeriods" 
              :key="period.value"
              @click="selectedTrendPeriod = period.value"
              class="px-2 py-1 text-sm rounded-md mr-1"
              :class="selectedTrendPeriod === period.value ? 'bg-blue-100 text-blue-800' : 'text-gray-500 hover:bg-gray-100'"
            >
              {{ period.label }}
            </button>
          </div>
        </div>
        
        <LearningTrendChart :data="trendData" :title="`${selectedTrendPeriod}学习时长`" />
      </div>
      
      <!-- 知识点掌握情况 -->
      <div class="bg-white p-6 rounded-lg shadow-md border border-gray-200 mb-6">
        <div class="flex justify-between items-center mb-4">
          <h3 class="text-lg font-semibold">知识点掌握情况</h3>
          <div class="flex items-center">
            <select 
              v-model="selectedCourseId" 
              class="border-gray-300 rounded-md text-sm focus:ring-blue-500 focus:border-blue-500"
            >
              <option value="">所有课程</option>
              <option v-for="course in realCourses" :key="course.id" :value="String(course.id)">
                {{ course.name }}
              </option>
            </select>
          </div>
        </div>
        
        <KnowledgeRadarChart :data="displayedKnowledgePoints" />
      </div>
      
      <!-- AI学习建议 -->
      <div class="mb-6">
        <AIAnalysisPanel :user-id="props.userId" :course-id="selectedCourseId" />
      </div>
      
      <!-- 课程详情 -->
      <div class="bg-white rounded-lg shadow-md border border-gray-200 overflow-hidden">
        <div class="px-6 py-4 border-b">
          <h3 class="text-lg font-semibold">课程学习详情</h3>
        </div>
        
        <div v-if="courseDetails.length === 0" class="p-6 text-center text-gray-500">
          暂无课程数据
        </div>
        
        <div v-else class="overflow-x-auto">
          <table class="min-w-full divide-y divide-gray-200">
            <thead class="bg-gray-50">
              <tr>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">课程名称</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">进度</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">学习时间</th>
                <th class="px-6 py-3 text-left text-xs font-medium text-gray-500 uppercase tracking-wider w-1/4">最后学习</th>
              </tr>
            </thead>
            <tbody class="bg-white divide-y divide-gray-200">
              <tr v-for="course in courseDetails" :key="course.id">
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="flex items-center">
                    <!-- 删除不能正常加载的图标 -->
                    <div class="ml-0">
                      <div class="text-sm font-medium text-gray-900">{{ course.name }}</div>
                      <div class="text-xs text-gray-500">{{ course.category }}</div>
                    </div>
                  </div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap">
                  <div class="w-full bg-gray-200 rounded-full h-2.5 max-w-[120px]">
                    <div class="bg-blue-600 h-2.5 rounded-full" :style="`width: ${course.progress}%`"></div>
                  </div>
                  <div class="text-xs text-gray-500 mt-1">{{ course.progress }}%</div>
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {{ course.learningTime }}小时
                </td>
                <td class="px-6 py-4 whitespace-nowrap text-sm text-gray-500">
                  {{ course.lastActivity }}
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue';
import LearningTrendChart from './LearningTrendChart.vue';
import CoursePieChart from './CoursePieChart.vue';
import KnowledgeRadarChart from './KnowledgeRadarChart.vue';
import AIAnalysisPanel from './AIAnalysisPanel.vue';
import { analyticsAPI } from '@/api';

interface KnowledgePoint {
  label: string;
  value: number;
}

interface CourseDetail {
  id: number;
  name: string;
  category: string;
  progress: number;
  learningTime: number;
  lastActivity: string;
  score: number;
}

const props = defineProps({
  userId: {
    type: [Number, String],
    required: true
  }
});

const loading = ref(true);
const errorMessage = ref('');

const overallProgress = ref(0);
const weeklyLearningTime = ref(0);
const previousWeekTime = ref(0);
const completedCourses = ref(0);
const inProgressCourses = ref(0);
const notStartedCourses = ref(0);

const trendPeriods = [
  { label: '周', value: 'week' },
  { label: '月', value: 'month' },
  { label: '年', value: 'year' }
];

const selectedTrendPeriod = ref('week');
const selectedCourseId = ref('');
const weekTrendData = ref<KnowledgePoint[]>([]);
const monthTrendData = ref<KnowledgePoint[]>([]);
const yearTrendData = ref<KnowledgePoint[]>([]);
const overallKnowledgePoints = ref<KnowledgePoint[]>([]);
const knowledgePointsByCourse = ref<Record<string, KnowledgePoint[]>>({});

const trendData = computed(() => {
  switch (selectedTrendPeriod.value) {
    case 'week':
      return weekTrendData.value;
    case 'month':
      return monthTrendData.value;
    case 'year':
      return yearTrendData.value;
    default:
      return weekTrendData.value;
  }
});

const courseDetails = ref<CourseDetail[]>([]);
const realCourses = computed(() =>
  courseDetails.value.map(course => ({
    id: course.id,
    name: course.name,
    category: course.category
  }))
);

const displayedKnowledgePoints = computed(() => {
  if (!selectedCourseId.value) {
    return overallKnowledgePoints.value;
  }
  return knowledgePointsByCourse.value[selectedCourseId.value] || overallKnowledgePoints.value;
});

watch(realCourses, courses => {
  if (courses.length === 0) {
    selectedCourseId.value = '';
    return;
  }

  const hasSelectedCourse = courses.some(course => String(course.id) === selectedCourseId.value);
  if (!hasSelectedCourse) {
    selectedCourseId.value = String(courses[0].id);
  }
}, { immediate: true });

onMounted(async () => {
  try {
    await fetchAnalyticsData();
  } catch (error) {
    console.error('初始化学习分析数据失败:', error);
  }
});

async function fetchAnalyticsData() {
  try {
    loading.value = true;

    if (!props.userId) {
      errorMessage.value = '当前用户信息不可用，无法加载学习分析数据。';
      return;
    }

    const response = await analyticsAPI.getStudentAnalytics(props.userId);
    const data = response.data || {};
    errorMessage.value = '';

    overallProgress.value = Number(data.overallProgress || 0);
    weeklyLearningTime.value = Number(data.weeklyLearningTime || 0);
    previousWeekTime.value = Number(data.previousWeekTime || 0);
    completedCourses.value = Number(data.completedCourses || 0);
    inProgressCourses.value = Number(data.inProgressCourses || 0);
    notStartedCourses.value = Number(data.notStartedCourses || 0);

    weekTrendData.value = Array.isArray(data.trendData?.week) ? data.trendData.week : [];
    monthTrendData.value = Array.isArray(data.trendData?.month) ? data.trendData.month : [];
    yearTrendData.value = Array.isArray(data.trendData?.year) ? data.trendData.year : [];
    courseDetails.value = Array.isArray(data.courseDetails) ? data.courseDetails : [];
    overallKnowledgePoints.value = Array.isArray(data.knowledgePoints) ? data.knowledgePoints : [];
    knowledgePointsByCourse.value = data.knowledgePointsByCourse && typeof data.knowledgePointsByCourse === 'object'
      ? data.knowledgePointsByCourse
      : {};
  } catch (error) {
    console.error('获取学习分析数据失败:', error);
    errorMessage.value = '学习分析数据加载失败，当前展示为空数据。';
    overallProgress.value = 0;
    weeklyLearningTime.value = 0;
    previousWeekTime.value = 0;
    completedCourses.value = 0;
    inProgressCourses.value = 0;
    notStartedCourses.value = 0;
    weekTrendData.value = [];
    monthTrendData.value = [];
    yearTrendData.value = [];
    courseDetails.value = [];
    overallKnowledgePoints.value = [];
    knowledgePointsByCourse.value = {};
  } finally {
    loading.value = false;
  }
}
</script>
