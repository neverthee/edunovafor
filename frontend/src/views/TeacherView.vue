<template>
  <div class="min-h-screen bg-gray-50">
    <div class="max-w-7xl mx-auto py-3 sm:px-6 lg:px-8">
      <div class="px-4 py-3 sm:px-0">
        <div id="teacher-lesson-planner-scroll-anchor" class="border-b border-gray-200 pb-2 mb-5">
          <div
            :class="activeTab === 'lesson-planner'
              ? 'flex flex-col gap-3 xl:flex-row xl:items-start xl:justify-between'
              : ''"
          >
            <div class="min-w-0">
              <h1 class="text-3xl font-bold text-gray-900">
                教师工作台
                <span v-if="activeTeacherTabLabel" class="ml-4 text-2xl font-semibold text-gray-900">{{ activeTeacherTabLabel }}</span>
              </h1>
              <p class="mt-2 text-sm text-gray-500">
                管理课程、创建教学内容和查看学生进度
              </p>
            </div>
            <div
              v-if="activeTab === 'lesson-planner'"
              id="teacher-lesson-planner-header-slot"
              class="w-full xl:max-w-[76%]"
            ></div>
          </div>
        </div>

        <!-- 欢迎页 -->
        <div v-if="activeTab === 'dashboard'">
          <WelcomeMessage
            v-model:activeTab="activeTab"
            :dashboard-overview="dashboardOverview"
          />
        </div>

        <!-- 课程列表 -->
        <div v-if="activeTab === 'courses'">
          <CourseList hide-header />
        </div>

        <div v-if="activeTab === 'my-classes'">
          <MyClasses hide-header />
        </div>

        <!-- 评估测试 -->
        <div v-if="activeTab === 'assessments'">
          <div v-if="showSubmissionsList">
            <div class="flex justify-between mb-4">
              <h2 class="text-xl font-semibold">{{ currentAssessment.title }} - 学生提交</h2>
              <button 
                @click="closeSubmissionsList" 
                class="px-4 py-2 border rounded-md hover:bg-gray-50"
              >
                返回评估列表
              </button>
            </div>
            <SubmissionList 
              :assessmentId="currentAssessment.id" 
              :role="'teacher'"
              @back="closeSubmissionsList"
            />
          </div>
          <div v-else>
            <AssessmentList 
              hide-header
              :role="'teacher'" 
              @view-submissions="viewSubmissions"
            />
          </div>
        </div>

        <!-- AI助手 -->
        <div v-if="activeTab === 'ai-assistant'">
          <AIAssistant :user-id="userId || ''" :course-id="assistantCourseId" />
        </div>

        <!-- 智能备课 -->
        <div v-if="activeTab === 'lesson-planner'">
          <LessonPlanner
            hide-header
            header-target="#teacher-lesson-planner-header-slot"
            scroll-anchor-target="#teacher-lesson-planner-scroll-anchor"
          />
        </div>

        <!-- 学习分析 -->
        <div v-if="activeTab === 'analytics'">
          <TeacherAnalytics hide-header />
        </div>

        <!-- 知识库 -->
        <div v-if="activeTab === 'knowledge-base'">
          <KnowledgeBase hide-header />
        </div>

        <!-- 最近活动 -->
        <div v-if="activeTab === 'dashboard'" class="mt-8">
          <h2 class="text-lg font-medium text-gray-900">最近活动</h2>
          <div class="mt-4 bg-white shadow overflow-hidden rounded-md">
            <ul class="divide-y divide-gray-200">
              <li v-if="!recentActivities || recentActivities.length === 0" class="px-6 py-4">
                暂无活动记录
              </li>
              <li v-else v-for="(activity, index) in recentActivities" :key="index" class="px-6 py-4">
                <div class="flex items-center space-x-4">
                  <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-gray-900 truncate">
                      {{ activity.title }}
                    </p>
                    <p class="text-sm text-gray-500 truncate">
                      {{ activity.description }}
                    </p>
                  </div>
                  <div class="text-sm text-gray-500">
                    {{ activity.time }}
                  </div>
                </div>
              </li>
            </ul>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRoute, useRouter } from 'vue-router';
import CourseList from '@/components/course/CourseList.vue';
import AIAssistant from '@/components/ai/AIAssistant.vue';
import LessonPlanner from '@/components/ai/LessonPlanner.vue';
import KnowledgeBase from '@/components/rag/KnowledgeBase.vue';
import WelcomeMessage from '@/components/WelcomeMessage.vue';
import AssessmentList from '@/components/assessment/AssessmentList.vue';
import SubmissionList from '@/components/assessment/SubmissionList.vue';
import TeacherAnalytics from '@/components/analytics/TeacherAnalytics.vue';
import MyClasses from '@/components/classroom/MyClasses.vue';
import { teacherTabs } from '@/config/dashboardTabs';
import { learningAPI } from '@/api';

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();
const userId = computed(() => authStore.user?.id);
const assistantCourseId = computed(() => {
  const rawCourseId = route.query.courseId;
  return typeof rawCourseId === 'string' && rawCourseId.trim() ? rawCourseId : undefined;
});

const tabs = teacherTabs;
const activeTab = computed({
  get: () => {
    const tab = route.query.activeTab;
    return typeof tab === 'string' && tabs.some(item => item.id === tab) ? tab : 'dashboard';
  },
  set: (tabId: string) => {
    router.replace({
      query: {
        ...route.query,
        activeTab: tabId
      }
    });
  }
});

const activeTeacherTabLabel = computed(() => {
  if (activeTab.value === 'dashboard') {
    return '';
  }
  return tabs.find(item => item.id === activeTab.value)?.name || '';
});

interface DashboardOverview {
  last_login_at?: string | null;
  notification_count?: number;
}

interface DashboardActivity {
  title: string;
  description: string;
  timestamp?: string;
  time?: string;
  type?: string;
}

// 评估测试相关状态
const showSubmissionsList = ref(false);
const currentAssessment = ref<{ id: string | number; title: string }>({ id: '', title: '' });
const dashboardOverview = ref<DashboardOverview | null>(null);

const viewSubmissions = (data: { assessment: { id: string | number; title: string } }) => {
  console.log('查看提交:', data);
  currentAssessment.value = {
    id: data.assessment.id,
    title: data.assessment.title
  };
  showSubmissionsList.value = true;
};

const closeSubmissionsList = () => {
  showSubmissionsList.value = false;
  currentAssessment.value = { id: '', title: '' };
};

const recentActivities = ref<DashboardActivity[]>([]);
let dashboardRefreshTimer: number | null = null;
let isFetchingDashboardSummary = false;

const formatRelativeTime = (timestamp?: string) => {
  if (!timestamp) {
    return '刚刚';
  }

  const date = new Date(timestamp);
  if (Number.isNaN(date.getTime())) {
    return '刚刚';
  }

  const diffMs = Date.now() - date.getTime();
  const diffMinutes = Math.floor(diffMs / (1000 * 60));

  if (diffMinutes < 1) {
    return '刚刚';
  }
  if (diffMinutes < 60) {
    return `${diffMinutes}分钟前`;
  }

  const diffHours = Math.floor(diffMinutes / 60);
  if (diffHours < 24) {
    return `${diffHours}小时前`;
  }

  const diffDays = Math.floor(diffHours / 24);
  if (diffDays === 1) {
    return '昨天';
  }
  if (diffDays < 7) {
    return `${diffDays}天前`;
  }

  return date.toLocaleDateString('zh-CN');
};

const loadDashboardSummary = async () => {
  if (isFetchingDashboardSummary) {
    return;
  }

  isFetchingDashboardSummary = true;
  try {
    const response = await learningAPI.getTeacherDashboardSummary() as any;
    dashboardOverview.value = response?.overview || null;
    recentActivities.value = Array.isArray(response?.recent_activities)
      ? response.recent_activities.map((activity: DashboardActivity) => ({
          ...activity,
          time: formatRelativeTime(activity.timestamp)
        }))
      : [];
  } catch (error) {
    console.error('获取教师工作台概览失败:', error);
  } finally {
    isFetchingDashboardSummary = false;
  }
};

const stopDashboardPolling = () => {
  if (dashboardRefreshTimer !== null) {
    window.clearInterval(dashboardRefreshTimer);
    dashboardRefreshTimer = null;
  }
};

const startDashboardPolling = () => {
  stopDashboardPolling();
  if (activeTab.value !== 'dashboard') {
    return;
  }

  void loadDashboardSummary();
  dashboardRefreshTimer = window.setInterval(() => {
    void loadDashboardSummary();
  }, 30000);
};

const handleWindowFocus = () => {
  if (activeTab.value === 'dashboard') {
    void loadDashboardSummary();
  }
};

watch(
  () => activeTab.value,
  (tab) => {
    if (tab === 'dashboard') {
      startDashboardPolling();
      return;
    }
    stopDashboardPolling();
  },
  { immediate: true }
);

onMounted(() => {
  window.addEventListener('focus', handleWindowFocus);
});

onBeforeUnmount(() => {
  stopDashboardPolling();
  window.removeEventListener('focus', handleWindowFocus);
});
</script>

<style scoped>
.btn {
  @apply px-4 py-2 border border-transparent text-sm font-medium rounded-md shadow-sm focus:outline-none focus:ring-2 focus:ring-offset-2;
}

.btn-primary {
  @apply text-white bg-blue-600 hover:bg-blue-700 focus:ring-blue-500;
}
</style>
