<template>
  <div class="space-y-8">
    <div v-if="!hideHeader" class="space-y-2">
      <h2 class="text-2xl font-bold text-slate-900">已加入课程</h2>
      <p class="text-sm text-slate-500">查看您已经加入的课程，并持续跟踪学习进度。</p>
    </div>

    <div class="grid grid-cols-1 gap-4 md:grid-cols-3">
      <div class="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <div class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">课程数</div>
        <div class="mt-3 text-3xl font-bold text-slate-900">{{ enrolledCourses.length }}</div>
        <div class="mt-1 text-sm text-slate-500">当前已加入课程</div>
      </div>
      <div class="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <div class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">平均进度</div>
        <div class="mt-3 text-3xl font-bold text-blue-600">{{ averageProgress }}%</div>
        <div class="mt-1 text-sm text-slate-500">按课程学习记录估算</div>
      </div>
      <div class="rounded-2xl border border-slate-100 bg-white p-5 shadow-sm">
        <div class="text-xs font-bold uppercase tracking-[0.2em] text-slate-400">学习中</div>
        <div class="mt-3 text-3xl font-bold text-emerald-600">{{ inProgressCount }}</div>
        <div class="mt-1 text-sm text-slate-500">有学习进度但尚未完成</div>
      </div>
    </div>

    <div class="rounded-3xl border border-slate-100 bg-white p-6 shadow-sm">
      <div class="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
        <div class="relative w-full max-w-xl">
          <input
            v-model.trim="filters.search"
            type="text"
            placeholder="搜索已加入课程..."
            class="h-12 w-full rounded-2xl border border-slate-200 bg-white pl-12 pr-4 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-4 focus:ring-blue-50"
          />
          <span class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400">
            <svg class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
            </svg>
          </span>
        </div>

        <div class="inline-flex rounded-2xl border border-slate-200 bg-slate-50 p-1">
          <button
            v-for="option in statusOptions"
            :key="option.value"
            type="button"
            @click="filters.status = option.value"
            class="rounded-xl px-4 py-2 text-sm font-semibold transition"
            :class="filters.status === option.value ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500 hover:text-slate-700'"
          >
            {{ option.label }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-16">
      <div class="h-12 w-12 animate-spin rounded-full border-b-2 border-t-2 border-blue-500"></div>
    </div>

    <div v-else-if="filteredCourses.length === 0" class="rounded-3xl border border-dashed border-slate-200 bg-white px-6 py-16 text-center shadow-sm">
      <div class="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-slate-100 text-slate-400">
        <svg class="h-7 w-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="1.8" d="M12 6.253v13m0-13C10.832 5.477 9.246 5 7.5 5S4.168 5.477 3 6.253v13C4.168 18.477 5.754 18 7.5 18s3.332.477 4.5 1.253m0-13C13.168 5.477 14.754 5 16.5 5c1.747 0 3.332.477 4.5 1.253v13C19.832 18.477 18.247 18 16.5 18c-1.746 0-3.332.477-4.5 1.253" />
        </svg>
      </div>
      <h3 class="mt-4 text-lg font-bold text-slate-900">暂无匹配课程</h3>
      <p class="mt-2 text-sm text-slate-500">可以前往“课程目录”加入新课程，或调整当前筛选条件。</p>
    </div>

    <div v-else class="grid grid-cols-1 gap-8 md:grid-cols-2 xl:grid-cols-3">
      <article
        v-for="course in filteredCourses"
        :key="course.id"
        class="group flex h-full flex-col overflow-hidden rounded-3xl border border-slate-100 bg-white shadow-sm transition-all duration-300 hover:-translate-y-1 hover:shadow-xl"
      >
        <div class="relative h-48 overflow-hidden bg-slate-50">
          <img
            :src="course.cover_image ? `${apiOrigin}${course.cover_image}` : defaultCourseImage"
            alt="课程封面"
            class="h-full w-full object-cover transition-transform duration-500 group-hover:scale-105"
          />
          <div class="absolute left-4 top-4">
            <span class="rounded-lg border border-slate-200/60 bg-white/90 px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider text-slate-700 shadow-sm backdrop-blur-md">
              {{ course.category || '通用课程' }}
            </span>
          </div>
          <div class="absolute right-4 top-4">
            <span class="rounded-lg border px-2.5 py-1 text-[11px] font-bold shadow-sm backdrop-blur-md" :class="difficultyBadgeClass(course.difficulty)">
              {{ difficultyText(course.difficulty) }}
            </span>
          </div>
        </div>

        <div class="flex flex-1 flex-col p-6">
          <div class="flex-1">
            <div class="flex items-start justify-between gap-3">
              <div>
                <h3 class="line-clamp-1 text-xl font-bold text-slate-900 transition-colors group-hover:text-blue-600">{{ course.name }}</h3>
                <p class="mt-1 text-sm text-slate-500">{{ course.teacher_name || '主讲教师' }}</p>
              </div>
              <span class="shrink-0 rounded-full px-2.5 py-1 text-xs font-bold" :class="progressPillClass(course.progress)">
                {{ progressStatusText(course.progress) }}
              </span>
            </div>

            <p class="mt-3 h-10 line-clamp-2 text-sm leading-relaxed text-slate-500">
              {{ course.description || '暂无课程描述信息...' }}
            </p>

            <div class="mt-6 rounded-2xl bg-slate-50 px-4 py-4">
              <div class="flex items-center justify-between text-sm">
                <span class="font-semibold text-slate-700">学习进度</span>
                <span class="font-bold text-slate-900">{{ course.progress }}%</span>
              </div>
              <div class="mt-3 h-2.5 overflow-hidden rounded-full bg-slate-200">
                <div class="h-full rounded-full bg-gradient-to-r from-blue-500 to-indigo-600 transition-all" :style="{ width: `${course.progress}%` }"></div>
              </div>
              <div class="mt-3 flex items-center justify-between text-xs text-slate-500">
                <span>学习时长 {{ formatLearningTime(course.learningTime) }}</span>
                <span>{{ formatLastActivity(course.lastActivity) }}</span>
              </div>
            </div>
          </div>

          <div class="mt-6 grid grid-cols-2 gap-3">
            <router-link
              :to="`/course/${course.id}`"
              class="flex items-center justify-center rounded-2xl border border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-50"
            >
              课程详情
            </router-link>
            <router-link
              :to="{ name: 'learning', params: { courseId: course.id } }"
              class="flex items-center justify-center rounded-2xl bg-blue-600 px-4 py-2.5 text-sm font-semibold text-white shadow-sm shadow-blue-200 transition hover:bg-blue-700"
            >
              继续学习
            </router-link>
          </div>
        </div>
      </article>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue';
import { analyticsAPI, courseAPI } from '@/api';
import { useAuthStore } from '@/stores/auth';
import { API_ORIGIN } from '@/config/api';
import defaultCourseImage from '@/assets/default-course.jpg';

interface AnalyticsCourseDetail {
  id: number;
  progress?: number;
  learningTime?: number;
  lastActivity?: string;
  score?: number;
}

interface StudentCourse {
  id: number;
  name: string;
  description: string;
  category?: string;
  difficulty?: string;
  teacher_name?: string;
  student_count?: number;
  is_public?: boolean;
  cover_image?: string;
  created_at?: string;
  updated_at?: string;
  progress: number;
  learningTime: number;
  lastActivity: string;
  score: number;
}

const props = withDefaults(defineProps<{
  hideHeader?: boolean;
}>(), {
  hideHeader: false
});

const authStore = useAuthStore();
const apiOrigin = API_ORIGIN;
const userId = computed(() => authStore.user?.id);
const loading = ref(true);
const enrolledCourses = ref<StudentCourse[]>([]);

const filters = reactive({
  search: '',
  status: 'all'
});

const statusOptions = [
  { label: '全部', value: 'all' },
  { label: '未开始', value: 'not-started' },
  { label: '学习中', value: 'in-progress' },
  { label: '已完成', value: 'completed' }
];

const averageProgress = computed(() => {
  if (enrolledCourses.value.length === 0) {
    return 0;
  }
  const total = enrolledCourses.value.reduce((sum, course) => sum + course.progress, 0);
  return Math.round(total / enrolledCourses.value.length);
});

const inProgressCount = computed(() =>
  enrolledCourses.value.filter(course => course.progress > 0 && course.progress < 100).length
);

const filteredCourses = computed(() => {
  const keyword = filters.search.trim().toLowerCase();

  return enrolledCourses.value.filter(course => {
    const matchesSearch = !keyword || [
      course.name,
      course.description,
      course.category,
      course.teacher_name
    ].some(field => String(field || '').toLowerCase().includes(keyword));

    if (!matchesSearch) {
      return false;
    }

    if (filters.status === 'completed') {
      return course.progress >= 100;
    }
    if (filters.status === 'in-progress') {
      return course.progress > 0 && course.progress < 100;
    }
    if (filters.status === 'not-started') {
      return course.progress <= 0;
    }

    return true;
  });
});

function difficultyBadgeClass(difficulty?: string) {
  switch (difficulty) {
    case 'beginner':
      return 'border-emerald-100 bg-emerald-50 text-emerald-600';
    case 'intermediate':
      return 'border-amber-100 bg-amber-50 text-amber-600';
    case 'advanced':
      return 'border-rose-100 bg-rose-50 text-rose-600';
    default:
      return 'border-slate-100 bg-slate-50 text-slate-600';
  }
}

function difficultyText(difficulty?: string) {
  switch (difficulty) {
    case 'beginner':
      return '初级';
    case 'intermediate':
      return '中级';
    case 'advanced':
      return '高级';
    default:
      return '未知';
  }
}

function progressPillClass(progress: number) {
  if (progress >= 100) {
    return 'bg-emerald-50 text-emerald-600';
  }
  if (progress > 0) {
    return 'bg-blue-50 text-blue-600';
  }
  return 'bg-slate-100 text-slate-500';
}

function progressStatusText(progress: number) {
  if (progress >= 100) {
    return '已完成';
  }
  if (progress > 0) {
    return '学习中';
  }
  return '未开始';
}

function formatLearningTime(hours?: number) {
  return `${Number(hours || 0).toFixed(1)}h`;
}

function formatLastActivity(lastActivity?: string) {
  if (!lastActivity || lastActivity === '未学习') {
    return '尚未学习';
  }

  const date = new Date(lastActivity);
  if (Number.isNaN(date.getTime())) {
    return lastActivity;
  }

  return `最近 ${date.toLocaleDateString('zh-CN')}`;
}

async function fetchStudentCourses() {
  loading.value = true;

  try {
    const courseRequest = courseAPI.getMyCourses();
    const analyticsRequest = userId.value
      ? analyticsAPI.getStudentAnalytics(userId.value)
      : Promise.resolve(null);

    const [courseResponse, analyticsResponse] = await Promise.all([courseRequest, analyticsRequest]);

    const courseDetails = ((analyticsResponse as any)?.data?.courseDetails || []) as AnalyticsCourseDetail[];
    const progressMap = new Map<number, AnalyticsCourseDetail>(
      courseDetails.map(item => [item.id, item])
    );

    enrolledCourses.value = (((courseResponse as any)?.courses || []) as Array<Record<string, any>>).map(course => {
      const detail = progressMap.get(Number(course.id));

      return {
        id: Number(course.id),
        name: String(course.name || ''),
        description: String(course.description || ''),
        category: course.category,
        difficulty: course.difficulty,
        teacher_name: course.teacher_name,
        student_count: course.student_count,
        is_public: course.is_public,
        cover_image: course.cover_image,
        created_at: course.created_at,
        updated_at: course.updated_at,
        progress: Math.max(0, Math.min(100, Number(detail?.progress || 0))),
        learningTime: Number(detail?.learningTime || 0),
        lastActivity: String(detail?.lastActivity || '未学习'),
        score: Number(detail?.score || 0)
      };
    }).sort((left, right) => {
      if (right.progress !== left.progress) {
        return right.progress - left.progress;
      }

      const leftTime = new Date(left.updated_at || left.created_at || 0).getTime();
      const rightTime = new Date(right.updated_at || right.created_at || 0).getTime();
      return rightTime - leftTime;
    });
  } catch (error) {
    console.error('获取学生课程失败:', error);
    enrolledCourses.value = [];
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  void fetchStudentCourses();
});
</script>
