<template>
  <div class="assessment-list">
    <div v-if="!props.hideHeader" class="mb-4">
      <h2 class="text-xl font-semibold text-slate-900">评估列表</h2>
    </div>
    
    <!-- 操作与过滤器 -->
    <div class="mb-6 flex flex-wrap items-end gap-4">
      <button 
        v-if="isTeacher"
        @click="createNewAssessment" 
        class="inline-flex h-[42px] items-center justify-center rounded-lg bg-blue-600 px-4 text-sm font-medium text-white transition hover:bg-blue-700"
      >
        新建评估
      </button>

      <div class="min-w-[260px] flex-1">
        <label class="mb-1 block text-sm font-medium text-slate-700">课程</label>
        <select 
          v-model="filters.courseId"
          class="h-[42px] w-full rounded-lg border border-slate-300 bg-white px-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        >
          <option value="">全部课程</option>
          <option v-for="course in courses" :key="course.id" :value="course.id">
            {{ course.name }}
          </option>
        </select>
      </div>

      <div class="min-w-[320px] flex-[1.2]">
        <label class="mb-1 block text-sm font-medium text-slate-700">名称</label>
        <input 
          type="text" 
          v-model="filters.search"
          placeholder="搜索评估标题..."
          class="h-[42px] w-full rounded-lg border border-slate-300 bg-white px-3 text-slate-900 outline-none transition focus:border-blue-500 focus:ring-2 focus:ring-blue-100"
        />
      </div>
    </div>
    
    <!-- 评估列表 -->
    <div v-if="loading" class="text-center py-10">
      <p class="text-gray-500">加载中...</p>
    </div>
    
    <div v-else-if="assessments.length === 0" class="text-center py-10 bg-gray-50 rounded-md">
      <p class="text-gray-500">暂无评估</p>
    </div>
    
    <div v-else class="space-y-4">
      <div 
        v-for="assessment in assessments" 
        :key="assessment.id"
        class="cursor-pointer rounded-lg border border-gray-200 bg-white p-6 shadow-md transition hover:border-blue-300 hover:shadow-lg"
        role="button"
        tabindex="0"
        @click="openAssessmentDetail(assessment)"
        @keydown.enter.prevent="openAssessmentDetail(assessment)"
        @keydown.space.prevent="openAssessmentDetail(assessment)"
      >
        <div class="flex justify-between items-start">
          <div>
            <h3 class="text-lg font-semibold">{{ assessment.title }}</h3>
            <p class="text-sm text-gray-600">{{ assessment.description }}</p>
            <div class="mt-2 flex flex-wrap gap-x-4 gap-y-2 text-sm text-gray-500">
              <span>课程: {{ getCourseNameById(assessment.course_id) }}</span>
              <span>总分: {{ assessment.total_score }}</span>
              <span>题目数: {{ getTotalQuestions(assessment) }}</span>
              <span>时间限制: {{ assessment.duration || '无限制' }}</span>
              <span>截止日期: {{ formatDate(assessment.due_date) }}</span>
              <span>尝试次数: {{ assessment.max_attempts || '无限制' }}</span>
              <span v-if="isTeacher">已发布班级: {{ formatPublishedClasses(assessment) }}</span>
            </div>
          </div>
          
          <div class="flex flex-col gap-2">
            <span 
              :class="getStatusClass(assessment)"
              class="px-2 py-1 text-xs rounded-full"
            >
              {{ getStatusText(assessment) }}
            </span>
            
            <div class="flex gap-2 mt-2">
              <router-link 
                :to="`/assessments/${assessment.id}`" 
                @click.stop
                class="text-blue-600 hover:text-blue-800"
              >
                查看
              </router-link>
              
              <span v-if="isTeacher" class="text-gray-300">|</span>
              
              <button 
                v-if="isTeacher"
                @click.stop="editAssessment(assessment)" 
                class="text-blue-600 hover:text-blue-800"
              >
                编辑
              </button>
              
              <span v-if="isTeacher" class="text-gray-300">|</span>

              <button
                v-if="isTeacher"
                @click.stop="openPublicationModal(assessment, 'publish')"
                class="text-emerald-600 hover:text-emerald-800"
              >
                发布
              </button>

              <span v-if="isTeacher" class="text-gray-300">|</span>

              <button
                v-if="isTeacher"
                @click.stop="openPublicationModal(assessment, 'unpublish')"
                class="text-amber-600 hover:text-amber-800"
              >
                取消发布
              </button>

              <span v-if="isTeacher" class="text-gray-300">|</span>
              
              <button 
                v-if="isTeacher"
                @click.stop="deleteAssessment(assessment)" 
                class="text-red-600 hover:text-red-800"
              >
                删除
              </button>
            </div>
          </div>
        </div>
        
        <!-- 学生提交状态 -->
        <div v-if="isStudent && assessment.submissions" class="mt-4 pt-4 border-t">
          <div class="flex justify-between items-center">
            <div>
              <p class="text-sm">
                <span class="font-medium">提交状态:</span>
                {{ assessment.submissions.length > 0 ? `已提交 ${assessment.submissions.length} 次` : '未提交' }}
              </p>
              <p v-if="assessment.submissions && assessment.submissions.length > 0" class="text-sm">
                <span class="font-medium">最高分:</span>
                {{ getHighestScore(assessment.submissions) }} / {{ assessment.total_score }}
              </p>
            </div>
            <div>
              <button 
                v-if="canTakeAssessment(assessment)"
                @click.stop="takeAssessment(assessment)" 
                class="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                {{ assessment.submissions && assessment.submissions.length > 0 ? '重新尝试' : '开始' }}
              </button>
              <button 
                v-else-if="assessment.submissions && assessment.submissions.length > 0"
                @click.stop="viewSubmissions(assessment)" 
                class="px-4 py-2 border rounded-md hover:bg-gray-50"
              >
                查看提交
              </button>
            </div>
          </div>
        </div>
        
        <!-- 教师查看提交 -->
        <div v-if="isTeacher" class="mt-4 pt-4 border-t">
          <div class="flex justify-between items-center">
            <p class="text-sm">
              <span class="font-medium">提交数:</span>
              {{ assessment.submission_count || 0 }}
            </p>
            <button 
              v-if="assessment.submission_count > 0"
              @click.stop="viewAllSubmissions(assessment)" 
              class="px-4 py-2 border rounded-md hover:bg-gray-50"
            >
              查看提交
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <!-- 分页 -->
    <div v-if="totalPages > 1" class="mt-6 flex justify-center">
      <div class="flex space-x-1">
        <button 
          @click="changePage(currentPage - 1)" 
          :disabled="currentPage === 1"
          class="px-3 py-1 border rounded-md"
          :class="currentPage === 1 ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50'"
        >
          上一页
        </button>
        
        <button 
          v-for="page in paginationRange" 
          :key="page"
          @click="changePage(page)"
          class="px-3 py-1 border rounded-md"
          :class="page === currentPage ? 'bg-blue-600 text-white' : 'hover:bg-gray-50'"
        >
          {{ page }}
        </button>
        
        <button 
          @click="changePage(currentPage + 1)" 
          :disabled="currentPage === totalPages"
          class="px-3 py-1 border rounded-md"
          :class="currentPage === totalPages ? 'opacity-50 cursor-not-allowed' : 'hover:bg-gray-50'"
        >
          下一页
        </button>
      </div>
    </div>
    
    <!-- 添加评估编辑器模态框 -->
    <div v-if="showEditor" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg w-full max-w-4xl max-h-[90vh] overflow-y-auto">
        <AssessmentEditor 
          :assessment="currentAssessment"
          @save="handleSaveAssessment"
          @cancel="showEditor = false"
        />
      </div>
    </div>

    <div v-if="showPublicationModal" class="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div class="w-full max-w-2xl rounded-2xl bg-white shadow-xl">
        <div class="border-b border-gray-200 px-6 py-4">
          <h3 class="text-xl font-bold text-gray-900">
            {{ publicationAction === 'publish' ? '发布评估' : '取消发布' }}
          </h3>
          <p class="mt-1 text-sm text-gray-500">
            {{ publicationAssessment?.title || '' }}
          </p>
        </div>

        <div class="space-y-4 px-6 py-5">
          <p class="text-sm text-gray-600">
            {{ publicationAction === 'publish'
              ? '选择要向哪些班级发布该评估，只有这些班级的学生可以看到。'
              : '选择要取消发布的班级，提交后这些班级学生将无法看到该评估。' }}
          </p>

          <div v-if="publicationLoading" class="rounded-xl bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
            班级数据加载中...
          </div>

          <div v-else-if="publicationClasses.length === 0" class="rounded-xl border border-dashed border-gray-300 bg-gray-50 px-4 py-8 text-center text-sm text-gray-500">
            暂无可选班级，请先到“我的班级”创建班级并添加学生。
          </div>

          <div v-else class="max-h-[320px] space-y-3 overflow-y-auto pr-1">
            <label
              v-for="teacherClass in publicationClasses"
              :key="teacherClass.id"
              class="flex cursor-pointer items-start justify-between rounded-xl border border-gray-200 px-4 py-3 transition hover:border-blue-300 hover:bg-blue-50/40"
            >
              <div>
                <p class="text-sm font-medium text-gray-900">{{ teacherClass.name }}</p>
                <p class="mt-1 text-xs text-gray-500">
                  {{ teacherClass.student_count || 0 }} 名学生
                  <span v-if="teacherClass.description"> · {{ teacherClass.description }}</span>
                </p>
              </div>
              <input
                v-model="selectedPublicationClassIds"
                :value="teacherClass.id"
                type="checkbox"
                class="mt-1 h-4 w-4 rounded border-gray-300 text-blue-600"
              />
            </label>
          </div>

          <p v-if="publicationError" class="text-sm text-red-500">{{ publicationError }}</p>
        </div>

        <div class="flex items-center justify-end gap-3 border-t border-gray-200 px-6 py-4">
          <button
            type="button"
            @click="closePublicationModal"
            class="rounded-lg border border-gray-300 px-4 py-2 text-gray-700"
          >
            取消
          </button>
          <button
            type="button"
            @click="submitPublicationUpdate"
            :disabled="publicationSubmitting || publicationLoading || publicationClasses.length === 0"
            class="rounded-lg px-4 py-2 text-white transition disabled:cursor-not-allowed disabled:bg-gray-400"
            :class="publicationAction === 'publish' ? 'bg-emerald-600 hover:bg-emerald-700' : 'bg-amber-500 hover:bg-amber-600'"
          >
            {{ publicationSubmitting ? '提交中...' : (publicationAction === 'publish' ? '确认发布' : '确认取消发布') }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted, watch } from 'vue';
import { useRouter } from 'vue-router';
import { useAuthStore } from '@/stores/auth';
import AssessmentEditor from './AssessmentEditor.vue';
import { courseAPI, assessmentAPI } from '@/api';
import notificationService from '@/services/notificationService';

const props = defineProps({
  courseId: {
    type: [Number, String],
    default: null
  },
  role: {
    type: String,
    default: 'student' // 'student', 'teacher'
  },
  hideHeader: {
    type: Boolean,
    default: false
  }
});

const emit = defineEmits(['create', 'edit', 'delete', 'take', 'view-submissions']);

const router = useRouter();
const authStore = useAuthStore();

// 状态变量
const assessments = ref([]);
const courses = ref([]);
const loading = ref(false);
const currentPage = ref(1);
const totalPages = ref(1);
const totalItems = ref(0);
const itemsPerPage = ref(10);

// 过滤器
const filters = ref({
  courseId: props.courseId || '',
  search: ''
});

// 计算属性
const isTeacher = computed(() => props.role === 'teacher');
const isStudent = computed(() => props.role === 'student');

const paginationRange = computed(() => {
  const range = [];
  const maxVisiblePages = 5;
  
  if (totalPages.value <= maxVisiblePages) {
    // 如果总页数小于等于最大可见页数，显示所有页码
    for (let i = 1; i <= totalPages.value; i++) {
      range.push(i);
    }
  } else {
    // 否则，显示当前页附近的页码
    let start = Math.max(1, currentPage.value - Math.floor(maxVisiblePages / 2));
    let end = Math.min(totalPages.value, start + maxVisiblePages - 1);
    
    // 调整起始页，确保显示正确数量的页码
    if (end - start + 1 < maxVisiblePages) {
      start = Math.max(1, end - maxVisiblePages + 1);
    }
    
    for (let i = start; i <= end; i++) {
      range.push(i);
    }
  }
  
  return range;
});

// 添加新的状态变量
const showEditor = ref(false);
const currentAssessment = ref(null);
const showPublicationModal = ref(false);
const publicationAction = ref('publish');
const publicationAssessment = ref(null);
const publicationClasses = ref([]);
const selectedPublicationClassIds = ref([]);
const publicationLoading = ref(false);
const publicationSubmitting = ref(false);
const publicationError = ref('');

// 方法
const fetchAssessments = async () => {
  loading.value = true;
  
  try {
    const normalizedCourseId = filters.value.courseId === '' || filters.value.courseId == null
      ? undefined
      : Number(filters.value.courseId);

    // 构建查询参数
    const params = {
      page: currentPage.value,
      per_page: itemsPerPage.value,
      search: filters.value.search || undefined
    };
    
    // 获取评估列表
    const response = await assessmentAPI.getAssessments(normalizedCourseId, params);
    
    assessments.value = response.assessments || [];
    totalItems.value = response.pagination?.total || 0;
    totalPages.value = response.pagination?.pages || 1;
    currentPage.value = response.pagination?.page || 1;
    
    // 如果是教师，获取每个评估的提交数量
    if (isTeacher.value) {
      await fetchSubmissionCounts();
    }
    
    // 如果是学生，获取提交状态
    if (isStudent.value) {
      await fetchStudentSubmissions();
    }
  } catch (error) {
    console.error('获取评估列表失败:', error);
  } finally {
    loading.value = false;
  }
};

// 获取提交数量
const fetchSubmissionCounts = async () => {
  try {
    // 为每个评估获取提交数量
    for (const assessment of assessments.value) {
      try {
        const response = await assessmentAPI.getSubmissionCount(assessment.id);
        assessment.submission_count = response.count || 0;
      } catch (err) {
        console.error(`获取评估 ${assessment.id} 的提交数量失败:`, err);
        assessment.submission_count = 0;
      }
    }
  } catch (error) {
    console.error('获取提交数量失败:', error);
  }
};

const fetchCourses = async () => {
  try {
    const response = await courseAPI.getMyCourses();
    courses.value = response.courses || [];
  } catch (error) {
    console.error('获取课程列表失败:', error);
  }
};

const fetchStudentSubmissions = async () => {
  try {
    if (!authStore.user?.id) {
      assessments.value.forEach(assessment => {
        assessment.submissions = [];
      });
      return;
    }

    const data = await assessmentAPI.getSubmissionsByStudent(authStore.user.id, {
      per_page: 200
    });

    // 将提交数据添加到对应的评估中
    assessments.value.forEach(assessment => {
      assessment.submissions = (data.submissions || []).filter(
        submission => submission.assessment_id === assessment.id
      );
    });
  } catch (error) {
    console.error('获取提交状态失败:', error);
    assessments.value.forEach(assessment => {
      assessment.submissions = [];
    });
  }
};

const changePage = (page) => {
  if (page < 1 || page > totalPages.value) return;
  currentPage.value = page;
  fetchAssessments();
};

const getCourseNameById = (courseId) => {
  const course = courses.value.find(c => String(c.id) === String(courseId));
  return course ? course.name : '未知课程';
};

const formatPublishedClasses = (assessment) => {
  if (!assessment?.published_classes?.length) return '未定向发布';
  return assessment.published_classes.map(item => item.name).join('、');
};

const getTotalQuestions = (assessment) => {
  if (!assessment) return 0;
  if (assessment.questions && Array.isArray(assessment.questions)) {
    return assessment.questions.length;
  }
  if (assessment.sections && Array.isArray(assessment.sections)) {
    return assessment.sections.reduce((total, section) => {
      return total + (section.questions ? section.questions.length : 0);
    }, 0);
  }
  return 0;
};

const formatDate = (dateString) => {
  if (!dateString) return '无截止日期';
  const date = new Date(dateString);
  return date.toLocaleDateString();
};

const getStatusText = (assessment) => {
  const now = new Date();
  const startDate = assessment.start_date ? new Date(assessment.start_date) : null;
  const dueDate = assessment.due_date ? new Date(assessment.due_date) : null;
  const isPublished = Boolean(
    assessment?.is_published || (assessment?.published_classes && assessment.published_classes.length > 0)
  );
  
  if (!isPublished) {
    return '未发布';
  } else if (startDate && now < startDate) {
    return '即将开始';
  } else if (dueDate && now > dueDate) {
    return '已结束';
  } else {
    return '进行中';
  }
};

const getStatusClass = (assessment) => {
  const status = getStatusText(assessment);
  
  switch (status) {
    case '未发布':
      return 'bg-gray-100 text-gray-800';
    case '即将开始':
      return 'bg-yellow-100 text-yellow-800';
    case '进行中':
      return 'bg-green-100 text-green-800';
    case '已结束':
      return 'bg-red-100 text-red-800';
    default:
      return 'bg-gray-100 text-gray-800';
  }
};

const getHighestScore = (submissions) => {
  if (!submissions || submissions.length === 0) return 0;
  return Math.max(...submissions.map(s => s.score || 0));
};

const canTakeAssessment = (assessment) => {
  const now = new Date();
  const startDate = assessment.start_date ? new Date(assessment.start_date) : null;
  const dueDate = assessment.due_date ? new Date(assessment.due_date) : null;
  
  // 检查评估是否激活
  if (!assessment.is_active) return false;
  
  // 检查是否在有效时间范围内
  if (startDate && now < startDate) return false;
  if (dueDate && now > dueDate) return false;
  
  // 检查尝试次数
  if (assessment.max_attempts && assessment.submissions) {
    if (assessment.submissions.length >= assessment.max_attempts) return false;
  }
  
  return true;
};

const createNewAssessment = () => {
  currentAssessment.value = {
    title: '',
    description: '',
    course_id: props.courseId || '',
    total_score: 100,
    questions: [],
    is_active: false
  };
  showEditor.value = true;
};

const handleSaveAssessment = async (assessment) => {
  try {
    if (assessment.id) {
      // 更新评估
      await assessmentAPI.updateAssessment(assessment.id, assessment);
    } else {
      // 创建评估
      await assessmentAPI.createAssessment(assessment);
    }
    showEditor.value = false;
    await fetchAssessments();
  } catch (error) {
    console.error('保存评估失败:', error);
  }
};

const openAssessmentDetail = (assessment) => {
  router.push(`/assessments/${assessment.id}`);
};

const editAssessment = (assessment) => {
  currentAssessment.value = { ...assessment };
  showEditor.value = true;
};

const deleteAssessment = async (assessment) => {
  if (!confirm('确定要删除这个评估吗？')) return;
  
  try {
    await assessmentAPI.deleteAssessment(assessment.id);
    await fetchAssessments();
  } catch (error) {
    console.error('删除评估失败:', error);
  }
};

const takeAssessment = (assessment) => {
  emit('take', assessment);
  router.push(`/assessments/${assessment.id}/take`);
};

const viewSubmissions = (assessment) => {
  emit('view-submissions', { assessment: assessment });
  router.push(`/assessments/${assessment.id}`);
};

const viewAllSubmissions = (assessment) => {
  emit('view-submissions', { assessment, student: false });
  // 或者直接导航到提交页面
  // router.push(`/assessments/${assessment.id}/all-submissions`);
};

const closePublicationModal = () => {
  showPublicationModal.value = false;
  publicationAssessment.value = null;
  publicationClasses.value = [];
  selectedPublicationClassIds.value = [];
  publicationError.value = '';
  publicationLoading.value = false;
  publicationSubmitting.value = false;
};

const openPublicationModal = async (assessment, action) => {
  showPublicationModal.value = true;
  publicationAction.value = action;
  publicationAssessment.value = assessment;
  publicationClasses.value = [];
  selectedPublicationClassIds.value = [];
  publicationLoading.value = true;
  publicationError.value = '';

  try {
    const response = await assessmentAPI.getPublication(assessment.id);
    const availableClasses = response.available_classes || [];
    const publishedClassIds = response.published_class_ids || [];
    publicationClasses.value = action === 'publish'
      ? availableClasses
      : availableClasses.filter(item => publishedClassIds.includes(item.id));
    selectedPublicationClassIds.value = action === 'publish'
      ? publishedClassIds.slice()
      : publishedClassIds.slice();
  } catch (error) {
    console.error('获取评估发布范围失败:', error);
    publicationError.value = error?.error || '获取班级列表失败';
  } finally {
    publicationLoading.value = false;
  }
};

const submitPublicationUpdate = async () => {
  if (!publicationAssessment.value) return;
  if (!selectedPublicationClassIds.value.length) {
    publicationError.value = '请至少选择一个班级';
    return;
  }

  publicationSubmitting.value = true;
  publicationError.value = '';

  try {
    const response = await assessmentAPI.updatePublication(publicationAssessment.value.id, {
      action: publicationAction.value,
      class_ids: selectedPublicationClassIds.value,
    });
    notificationService.success(
      publicationAction.value === 'publish' ? '发布成功' : '取消发布成功',
      response?.message || '操作已完成'
    );
    closePublicationModal();
    await fetchAssessments();
  } catch (error) {
    console.error('更新评估发布范围失败:', error);
    publicationError.value = error?.error || '提交失败，请稍后重试';
  } finally {
    publicationSubmitting.value = false;
  }
};

// 监听过滤器变化
watch(() => props.courseId, (newVal) => {
  if (newVal !== filters.value.courseId) {
    filters.value.courseId = newVal || '';
    currentPage.value = 1;
    fetchAssessments();
  }
});

// 初始化
onMounted(() => {
  fetchCourses();
  fetchAssessments();
});

// 监听过滤器变化
watch(filters, () => {
  fetchAssessments();
}, { deep: true });
</script> 
