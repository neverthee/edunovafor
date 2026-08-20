<template>
  <div class="min-h-screen bg-gray-50">
    <div class="mx-auto max-w-7xl py-3 sm:px-6 lg:px-8">
      <div class="px-4 py-3 sm:px-0">
        <div class="border-b border-gray-200 pb-2 mb-5">
          <h1 class="text-3xl font-bold text-gray-900">
            学习中心
            <span v-if="activeStudentTabLabel" class="ml-4 text-2xl font-semibold text-gray-900">{{ activeStudentTabLabel }}</span>
          </h1>
          <p class="mt-2 text-sm text-gray-500">
            探索课程、完成任务并持续跟踪您的学习进度
          </p>
        </div>

        <div v-if="activeTab === 'dashboard'">
          <WelcomeMessage
            v-model:activeTab="activeTab"
            :student-todo-items="studentTodoItems"
            :student-todo-loading="studentTodoLoading"
          />
        </div>

        <div v-if="activeTab === 'my-courses'">
          <StudentMyCourses hide-header />
        </div>

        <div v-if="activeTab === 'courses'">
          <CourseList hide-header />
        </div>

        <div v-if="activeTab === 'assessments'">
          <AssessmentList hide-header :role="'student'" />
        </div>

        <div v-if="activeTab === 'analytics'">
          <LearningAnalytics :user-id="userId || ''" />
        </div>

        <div v-if="activeTab === 'ai-assistant'">
          <AIAssistant :user-id="userId || ''" />
        </div>

        <div v-if="activeTab === 'knowledge-base'">
          <KnowledgeBase />
        </div>

        <div v-if="activeTab === 'ai-quiz'">
          <TestAIQuizView />
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref, watch } from 'vue';
import { useAuthStore } from '@/stores/auth';
import { useRoute, useRouter } from 'vue-router';
import { assessmentAPI, courseAPI } from '@/api';
import CourseList from '@/components/course/CourseList.vue';
import StudentMyCourses from '@/components/course/StudentMyCourses.vue';
import AssessmentList from '@/components/assessment/AssessmentList.vue';
import AIAssistant from '@/components/ai/AIAssistant.vue';
import LearningAnalytics from '@/components/analytics/LearningAnalytics.vue';
import KnowledgeBase from '@/components/rag/KnowledgeBase.vue';
import WelcomeMessage from '@/components/WelcomeMessage.vue';
import TestAIQuizView from '@/views/TestAIQuizView.vue';
import { studentTabs } from '@/config/dashboardTabs';

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

const authStore = useAuthStore();
const route = useRoute();
const router = useRouter();
const userId = computed(() => authStore.user?.id);

const tabs = studentTabs;
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

const activeStudentTabLabel = computed(() => {
  if (activeTab.value === 'dashboard') {
    return '';
  }
  return tabs.find(item => item.id === activeTab.value)?.name || '';
});

const studentTodoItems = ref<StudentTodoItem[]>([]);
const studentTodoLoading = ref(false);
const studentTodoInitialized = ref(false);
let dashboardRefreshTimer: number | null = null;
const DASHBOARD_REFRESH_INTERVAL = 5000;

function normalizeDateValue(value?: string | null) {
  if (!value) {
    return null;
  }

  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function sortTodoItems(items: StudentTodoItem[]) {
  return [...items].sort((left, right) => {
    const leftDue = normalizeDateValue(left.dueDate)?.getTime() ?? Number.MAX_SAFE_INTEGER;
    const rightDue = normalizeDateValue(right.dueDate)?.getTime() ?? Number.MAX_SAFE_INTEGER;

    if (leftDue !== rightDue) {
      return leftDue - rightDue;
    }

    return left.courseId - right.courseId;
  });
}

async function loadStudentTodoItems() {
  if (!userId.value) {
    studentTodoItems.value = [];
    studentTodoLoading.value = false;
    studentTodoInitialized.value = false;
    return;
  }

  const showLoadingState = !studentTodoInitialized.value;
  if (showLoadingState) {
    studentTodoLoading.value = true;
  }

  try {
    const [assessmentResponse, submissionsResponse, myCoursesResponse] = await Promise.all([
      assessmentAPI.getAssessments({ page: 1, per_page: 100 }),
      assessmentAPI.getSubmissionsByStudent(userId.value, { page: 1, per_page: 200 }),
      courseAPI.getMyCourses()
    ]);

    const assessments = ((assessmentResponse as any)?.assessments || []) as Array<Record<string, any>>;
    const submissions = ((submissionsResponse as any)?.submissions || []) as Array<Record<string, any>>;
    const myCourses = ((myCoursesResponse as any)?.courses || []) as Array<Record<string, any>>;
    const courseNameMap = new Map<number, string>(
      myCourses.map(course => [Number(course.id), String(course.name || `课程 ${course.id}`)])
    );
    const submittedAssessmentIds = new Set<number>(
      submissions.map(submission => Number(submission.assessment_id))
    );
    const now = new Date();

    const pendingItems = assessments.filter(assessment => {
      if (submittedAssessmentIds.has(Number(assessment.id))) {
        return false;
      }

      if (assessment.is_active === false) {
        return false;
      }

      const startDate = normalizeDateValue(assessment.start_date);
      const dueDate = normalizeDateValue(assessment.due_date);

      if (startDate && startDate > now) {
        return false;
      }

      if (dueDate && dueDate < now) {
        return false;
      }

      return true;
    }).map(assessment => ({
      id: Number(assessment.id),
      title: String(assessment.title || '未命名任务'),
      description: String(assessment.description || ''),
      type: String(assessment.type || 'quiz'),
      courseId: Number(assessment.course_id),
      courseName: courseNameMap.get(Number(assessment.course_id)) || `课程 ${assessment.course_id}`,
      dueDate: assessment.due_date || null,
      startDate: assessment.start_date || null
    }));

    studentTodoItems.value = sortTodoItems(pendingItems);
    studentTodoInitialized.value = true;
  } catch (error) {
    console.error('获取学生待办事项失败:', error);
    studentTodoItems.value = [];
  } finally {
    if (showLoadingState) {
      studentTodoLoading.value = false;
    }
  }
}

function stopDashboardPolling() {
  if (dashboardRefreshTimer !== null) {
    window.clearInterval(dashboardRefreshTimer);
    dashboardRefreshTimer = null;
  }
}

function startDashboardPolling() {
  stopDashboardPolling();

  if (activeTab.value !== 'dashboard') {
    return;
  }

  void loadStudentTodoItems();
  dashboardRefreshTimer = window.setInterval(() => {
    void loadStudentTodoItems();
  }, DASHBOARD_REFRESH_INTERVAL);
}

function handleWindowFocus() {
  if (activeTab.value === 'dashboard') {
    void loadStudentTodoItems();
  }
}

function handleVisibilityChange() {
  if (document.visibilityState === 'visible' && activeTab.value === 'dashboard') {
    void loadStudentTodoItems();
  }
}

watch(
  () => activeTab.value,
  tab => {
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
  document.addEventListener('visibilitychange', handleVisibilityChange);
});

onBeforeUnmount(() => {
  stopDashboardPolling();
  window.removeEventListener('focus', handleWindowFocus);
  document.removeEventListener('visibilitychange', handleVisibilityChange);
});
</script>
