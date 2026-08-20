<template>
  <div class="course-list">
    <div v-if="!props.hideHeader" class="mb-4">
      <h2 class="text-2xl font-bold">课程列表</h2>
    </div>

    <div class="mb-10 p-1">
      <div class="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
        <!-- 左侧：搜索 -->
        <div class="flex-1 max-w-md">
          <div class="relative group">
            <input 
              type="text" 
              v-model="filters.search" 
              placeholder="搜索感兴趣的课程..." 
              class="h-[48px] w-full rounded-2xl border border-slate-200 bg-white pl-12 pr-4 text-slate-900 outline-none transition-all focus:border-blue-500 focus:ring-4 focus:ring-blue-50/50 shadow-sm group-hover:border-slate-300"
            />
            <span class="absolute left-4 top-1/2 -translate-y-1/2 text-slate-400 group-focus-within:text-blue-500 transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M21 21l-6-6m2-5a7 7 0 11-14 0 7 7 0 0114 0z" />
              </svg>
            </span>
          </div>
        </div>

        <!-- 右侧：筛选和创建 -->
        <div class="flex flex-wrap items-center gap-4">
          <div class="flex items-center bg-slate-100/50 p-1 rounded-2xl border border-slate-200/60">
            <select
              v-model="filters.category"
              class="h-[40px] rounded-xl bg-transparent border-none px-4 text-sm font-medium text-slate-700 outline-none focus:ring-0 min-w-[130px]"
            >
              <option value="">所有分类</option>
              <option v-for="category in categoryOptions" :key="category" :value="category">
                {{ category }}
              </option>
            </select>
            <div class="w-px h-4 bg-slate-200 mx-1"></div>
            <select
              v-model="filters.difficulty"
              class="h-[40px] rounded-xl bg-transparent border-none px-4 text-sm font-medium text-slate-700 outline-none focus:ring-0 min-w-[130px]"
            >
              <option value="">所有难度</option>
              <option value="beginner">初级</option>
              <option value="intermediate">中级</option>
              <option value="advanced">高级</option>
            </select>
          </div>

          <button 
            v-if="userRole === 'teacher' || userRole === 'admin'"
            @click="openCreateModal()" 
            class="inline-flex h-[48px] items-center justify-center rounded-2xl bg-blue-600 px-6 text-sm font-bold text-white transition-all hover:bg-blue-700 hover:shadow-lg hover:shadow-blue-200 active:scale-[0.98]"
          >
            <svg xmlns="http://www.w3.org/2000/svg" class="h-5 w-5 mr-2" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4v16m8-8H4" />
            </svg>
            创建新课程
          </button>
        </div>
      </div>
    </div>

    <div v-if="loading" class="flex justify-center py-10">
      <div class="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-blue-500"></div>
    </div>

    <div v-else-if="courses.length === 0" class="text-center py-10 bg-gray-50 rounded-md">
      <p class="text-gray-500">暂无课程</p>
    </div>

    <div v-else class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-8">
      <div v-for="course in courses" :key="course.id" class="group bg-white rounded-xl shadow-sm hover:shadow-xl transition-all duration-300 border border-slate-100 flex flex-col h-full overflow-hidden">
        <!-- 课程封面区域 -->
        <div class="h-48 bg-slate-50 relative overflow-hidden shrink-0">
          <img 
            :src="course.cover_image ? `${apiOrigin}${course.cover_image}` : defaultCourseImage" 
            alt="课程封面" 
            class="w-full h-full object-cover transition-transform duration-500 group-hover:scale-105" 
          />
          
          <!-- 分类标签 -->
          <div class="absolute top-4 left-4 z-10">
            <span class="px-2.5 py-1 text-[11px] font-bold uppercase tracking-wider bg-white/90 backdrop-blur-md rounded-lg text-slate-700 shadow-sm border border-slate-200/50">
              {{ course.category || '通用课程' }}
            </span>
          </div>

          <!-- 难度标签 (浮动在图片上) -->
          <div class="absolute top-4 right-4 z-10">
            <span class="px-2.5 py-1 text-[11px] font-bold rounded-lg shadow-sm border backdrop-blur-md" :class="difficultyBadgeClass(course.difficulty)">
              {{ difficultyText(course.difficulty) }}
            </span>
          </div>
        </div>

        <!-- 课程信息区域 -->
        <div class="p-6 flex flex-col flex-1">
          <div class="flex-1">
            <h3 class="text-xl font-bold text-slate-900 group-hover:text-blue-600 transition-colors line-clamp-1 mb-2">{{ course.name }}</h3>
            <p class="text-slate-500 text-sm line-clamp-2 leading-relaxed h-10">{{ course.description || '暂无课程描述信息...' }}</p>
          </div>

          <div class="mt-6 pt-5 border-t border-slate-50 flex items-center justify-between">
            <div class="flex items-center space-x-2">
              <div class="w-8 h-8 rounded-full bg-blue-50 flex items-center justify-center text-blue-600 font-bold text-xs">
                {{ course.teacher_name?.charAt(0) || 'T' }}
              </div>
              <span class="text-sm font-medium text-slate-600">{{ course.teacher_name || '主讲教师' }}</span>
            </div>
            
            <div class="flex items-center text-slate-400 text-xs">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-4 w-4 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 4.354a4 4 0 110 5.292M15 21H3v-1a6 6 0 0112 0v1zm0 0h6v-1a6 6 0 00-9-5.197M13 7a4 4 0 11-8 0 4 4 0 018 0z" />
              </svg>
              {{ course.student_count || 0 }} 人已学
            </div>
          </div>

          <!-- 底部操作按钮 -->
          <div class="mt-5 grid grid-cols-2 gap-3">
            <router-link 
              :to="`/course/${course.id}`" 
              class="flex items-center justify-center px-4 py-2.5 rounded-xl border border-slate-200 text-sm font-semibold text-slate-700 hover:bg-slate-50 transition-colors"
            >
              课程详情
            </router-link>
            <button
              v-if="userRole === 'student' && !course.is_enrolled"
              type="button"
              @click="enrollInCourse(course)"
              :disabled="enrollingCourseId === course.id"
              class="flex items-center justify-center px-4 py-2.5 rounded-xl bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 shadow-sm shadow-blue-200 transition-all active:scale-[0.98] disabled:cursor-not-allowed disabled:bg-blue-300"
            >
              {{ enrollingCourseId === course.id ? '加入中...' : '加入课程' }}
            </button>
            <router-link 
              v-else
              :to="{ name: 'learning', params: { courseId: course.id } }" 
              class="flex items-center justify-center px-4 py-2.5 rounded-xl bg-blue-600 text-sm font-semibold text-white hover:bg-blue-700 shadow-sm shadow-blue-200 transition-all active:scale-[0.98]"
            >
              {{ userRole === 'student' ? '继续学习' : '立即学习' }}
            </router-link>
          </div>

          <!-- 管理操作 (仅教师/管理员可见) -->
          <div v-if="userRole === 'teacher' || userRole === 'admin'" class="mt-3 flex items-center justify-end space-x-4 px-1">
            <button @click="openEditModal(course)" class="text-xs font-medium text-slate-400 hover:text-blue-600 flex items-center transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
              </svg>
              编辑
            </button>
            <button @click="confirmDeleteCourse(course)" class="text-xs font-medium text-slate-400 hover:text-red-600 flex items-center transition-colors">
              <svg xmlns="http://www.w3.org/2000/svg" class="h-3.5 w-3.5 mr-1" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
              </svg>
              删除
            </button>
          </div>
        </div>
      </div>
    </div>

    <div class="mt-6 flex justify-center">
      <nav class="flex items-center">
        <button 
          @click="changePage(currentPage - 1)" 
          :disabled="currentPage === 1" 
          class="px-3 py-1 rounded-md border"
          :class="currentPage === 1 ? 'text-gray-400 cursor-not-allowed' : 'hover:bg-gray-100'"
        >
          上一页
        </button>
        <span class="mx-4">{{ currentPage }} / {{ totalPages }}</span>
        <button 
          @click="changePage(currentPage + 1)" 
          :disabled="currentPage === totalPages" 
          class="px-3 py-1 rounded-md border"
          :class="currentPage === totalPages ? 'text-gray-400 cursor-not-allowed' : 'hover:bg-gray-100'"
        >
          下一页
        </button>
      </nav>
    </div>

    <!-- 创建/编辑课程模态框 -->
    <div v-if="showCreateModal" class="fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50">
      <div class="bg-white rounded-lg p-6 w-full max-w-2xl max-h-[90vh] overflow-y-auto">
        <h3 class="text-xl font-bold mb-4">{{ isEditing ? '编辑课程' : '创建新课程' }}</h3>
        <form @submit.prevent="saveCourse">
          <div class="mb-4">
            <label class="block text-gray-700 text-sm font-bold mb-2">课程名称 <span class="text-red-500">*</span></label>
            <input v-model="newCourse.name" type="text" required class="w-full px-3 py-2 border rounded-md" />
          </div>
          <div class="mb-4">
            <label class="block text-gray-700 text-sm font-bold mb-2">课程描述 <span class="text-red-500">*</span></label>
            <textarea v-model="newCourse.description" required class="w-full px-3 py-2 border rounded-md" rows="3"></textarea>
          </div>
          <div class="mb-4 grid grid-cols-2 gap-4">
            <div>
              <label class="block text-gray-700 text-sm font-bold mb-2">分类 <span class="text-red-500">*</span></label>
              <input
                v-model.trim="newCourse.category"
                list="course-category-options"
                required
                class="w-full px-3 py-2 border rounded-md"
                placeholder="输入分类或选择已有分类"
              />
              <datalist id="course-category-options">
                <option v-for="category in categoryOptions" :key="`category-${category}`" :value="category" />
              </datalist>
              <p class="mt-2 text-xs text-gray-500">支持手动输入，也支持直接选择已有分类。</p>
            </div>
            <div>
              <label class="block text-gray-700 text-sm font-bold mb-2">难度 <span class="text-red-500">*</span></label>
              <select v-model="newCourse.difficulty" required class="w-full px-3 py-2 border rounded-md">
                <option value="beginner">初级</option>
                <option value="intermediate">中级</option>
                <option value="advanced">高级</option>
              </select>
            </div>
          </div>
          <div class="mb-4">
            <div class="flex items-center">
              <input type="checkbox" id="is-public" v-model="newCourse.is_public" class="mr-2" />
              <label for="is-public" class="text-gray-700 text-sm font-bold">公开课程</label>
            </div>
          </div>
          <div v-if="!isEditing" class="mb-4 rounded-lg border border-dashed border-gray-300 p-4">
            <div class="flex items-center justify-between gap-4">
              <div>
                <label class="block text-gray-700 text-sm font-bold">课件资源（可选）</label>
                <p class="mt-1 text-xs text-gray-500">课程创建成功后会自动上传这些资源，可多次选择文件并累积添加。</p>
              </div>
              <label class="inline-flex cursor-pointer items-center rounded-md bg-gray-100 px-3 py-2 text-sm text-gray-700 hover:bg-gray-200">
                选择文件
                <input type="file" multiple class="hidden" @change="handleCourseMaterialsChange" />
              </label>
            </div>
            <div v-if="newCourseMaterialFiles.length > 0" class="mt-4 space-y-2">
              <div
                v-for="(file, index) in newCourseMaterialFiles"
                :key="`${file.name}-${index}`"
                class="flex items-center justify-between rounded-md bg-gray-50 px-3 py-2 text-sm text-gray-600"
              >
                <span class="truncate pr-4">{{ file.name }}</span>
                <button type="button" @click="removeCourseMaterial(index)" class="text-red-500 hover:text-red-700">
                  移除
                </button>
              </div>
            </div>
            <p v-else class="mt-4 text-sm text-gray-500">未选择课件资源。</p>
          </div>
          <div class="flex justify-end gap-2 mt-6">
            <button type="button" @click="closeCreateModal" class="px-4 py-2 border rounded-md">取消</button>
            <button type="submit" class="px-4 py-2 bg-blue-600 text-white rounded-md">
              {{ isEditing ? '保存' : '创建' }}
            </button>
          </div>
        </form>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted, computed, watch, onBeforeUnmount } from 'vue';
import { useAuthStore } from '../../stores/auth';
import { courseAPI, materialAPI } from '../../api';
import notificationService from '../../services/notificationService';
import dialogService from '../../services/dialogService';
import { API_ORIGIN } from '@/config/api';
import defaultCourseImage from '@/assets/default-course.jpg';
import axios from 'axios';

const props = withDefaults(defineProps<{
  hideHeader?: boolean;
}>(), {
  hideHeader: false
});

// 定义Course接口
interface Course {
  id: number;
  name: string;
  description: string;
  category?: string;
  difficulty?: string;
  teacher_name?: string;
  student_count?: number;
  is_public?: boolean;
  is_enrolled?: boolean;
  cover_image?: string;
  created_at?: string;
  updated_at?: string;
}

const authStore = useAuthStore();
const apiOrigin = API_ORIGIN;
const userRole = computed(() => authStore.user?.role || '');
const defaultCategoryOptions = ['计算机科学', '数学', '语言', '自然科学', '人工智能'];

const courses = ref<Course[]>([]);
const loading = ref(true);
const enrollingCourseId = ref<number | null>(null);
const currentPage = ref(1);
const totalPages = ref(1);
const showCreateModal = ref(false);
const isEditing = ref(false);
const currentCourseId = ref<number | null>(null);
const newCourseMaterialFiles = ref<File[]>([]);

const filters = reactive({
  search: '',
  category: '',
  difficulty: ''
});

const newCourse = reactive({
  name: '',
  description: '',
  category: '计算机科学',
  difficulty: 'beginner',
  is_public: true
});

const categoryOptions = computed(() => {
  const categories = new Set(defaultCategoryOptions);
  courses.value.forEach(course => {
    if (course.category?.trim()) {
      categories.add(course.category.trim());
    }
  });
  if (newCourse.category.trim()) {
    categories.add(newCourse.category.trim());
  }
  return Array.from(categories);
});

onMounted(async () => {
  await fetchCourses();
});

watch([() => filters.category, () => filters.difficulty], () => {
  currentPage.value = 1; // 重置到第一页
  fetchCourses();
});

// 监听搜索框变化，添加防抖
let searchTimeout: number | null = null;
watch(() => filters.search, () => {
  if (searchTimeout) {
    clearTimeout(searchTimeout);
  }
  searchTimeout = window.setTimeout(() => {
    currentPage.value = 1; // 重置到第一页
    fetchCourses();
  }, 500); // 500ms防抖
});

async function fetchCourses() {
  loading.value = true;
  try {
    console.log('开始获取课程列表，筛选参数:', {
      page: currentPage.value,
      per_page: 9,
      search: filters.search,
      category: filters.category,
      difficulty: filters.difficulty
    });
    
    // 调用API获取课程列表
    const response = await courseAPI.getCourses({
      page: currentPage.value,
      per_page: 9,
      search: filters.search,
      category: filters.category,
      difficulty: filters.difficulty
    });
    
    console.log('课程API响应:', response);
    
    // 处理API响应数据
    const responseData = response as any; // 类型断言为any以避免TypeScript错误
    if (responseData && responseData.courses) {
      courses.value = [...responseData.courses].sort((left, right) => {
        const leftTime = new Date(left.updated_at || left.created_at || 0).getTime();
        const rightTime = new Date(right.updated_at || right.created_at || 0).getTime();
        return rightTime - leftTime;
      });
      totalPages.value = responseData.pages || 1;
      currentPage.value = responseData.current_page || responseData.page || 1;
      console.log('课程数据设置完成:', {
        课程数量: courses.value.length,
        总页数: totalPages.value,
        当前页: currentPage.value
      });
    } else {
      console.warn('API返回格式不符合预期:', response);
      courses.value = [];
      totalPages.value = 1;
    }
    loading.value = false;
  } catch (error) {
    console.error('获取课程失败:', error);
    loading.value = false;
  }
}

async function enrollInCourse(course: Course) {
  if (enrollingCourseId.value !== null) {
    return;
  }

  enrollingCourseId.value = course.id;
  try {
    await courseAPI.enrollCourse(course.id);
    course.is_enrolled = true;
    course.student_count = Number(course.student_count || 0) + 1;
    notificationService.success('加入课程成功', `已加入 "${course.name}"，现在可以在“我的课程”中继续学习`);
  } catch (error) {
    console.error('加入课程失败:', error);
    notificationService.error('加入课程失败', '当前课程暂时无法加入，请稍后重试');
  } finally {
    enrollingCourseId.value = null;
  }
}

function changePage(page: number) {
  if (page < 1 || page > totalPages.value) return;
  currentPage.value = page;
  fetchCourses();
}

function difficultyBadgeClass(difficulty: string | undefined) {
  switch (difficulty) {
    case 'beginner': return 'bg-emerald-50 text-emerald-600 border-emerald-100';
    case 'intermediate': return 'bg-amber-50 text-amber-600 border-amber-100';
    case 'advanced': return 'bg-rose-50 text-rose-600 border-rose-100';
    default: return 'bg-slate-50 text-slate-600 border-slate-100';
  }
}

function difficultyText(difficulty: string | undefined) {
  switch (difficulty) {
    case 'beginner': return '初级';
    case 'intermediate': return '中级';
    case 'advanced': return '高级';
    default: return '未知';
  }
}

function resetCourseForm() {
  Object.assign(newCourse, {
    name: '',
    description: '',
    category: '计算机科学',
    difficulty: 'beginner',
    is_public: true
  });
  newCourseMaterialFiles.value = [];
}

function openCreateModal() {
  resetCourseForm();
  isEditing.value = false;
  currentCourseId.value = null;
  showCreateModal.value = true;
}

function closeCreateModal() {
  showCreateModal.value = false;
  resetCourseForm();
}

function openEditModal(course: Course) {
  // 填充表单数据
  Object.assign(newCourse, {
    name: course.name,
    description: course.description,
    category: course.category || '计算机科学',
    difficulty: course.difficulty || 'beginner',
    is_public: course.is_public !== false
  });
  newCourseMaterialFiles.value = [];
  isEditing.value = true;
  currentCourseId.value = course.id;
  showCreateModal.value = true;
}

function mergeCourseMaterialFiles(existingFiles: File[], incomingFiles: File[]) {
  const merged = [...existingFiles];
  const fileKeys = new Set(existingFiles.map(file => `${file.name}::${file.size}::${file.lastModified}`));

  for (const file of incomingFiles) {
    const key = `${file.name}::${file.size}::${file.lastModified}`;
    if (fileKeys.has(key)) {
      continue;
    }
    merged.push(file);
    fileKeys.add(key);
  }

  return merged;
}

function handleCourseMaterialsChange(event: Event) {
  const target = event.target as HTMLInputElement;
  if (!target.files?.length) {
    return;
  }

  newCourseMaterialFiles.value = mergeCourseMaterialFiles(
    newCourseMaterialFiles.value,
    Array.from(target.files)
  );
  target.value = '';
}

function removeCourseMaterial(index: number) {
  newCourseMaterialFiles.value.splice(index, 1);
}

async function uploadInitialMaterials(courseId: number, files: File[]) {
  let uploadedCount = 0;
  const failedFiles: string[] = [];

  for (const file of files) {
    try {
      const formData = new FormData();
      formData.append('file', file);
      formData.append('title', file.name);
      await materialAPI.uploadMaterial(courseId, formData);
      uploadedCount += 1;
    } catch (error) {
      console.error('初始课件上传失败:', file.name, error);
      failedFiles.push(file.name);
    }
  }

  return { uploadedCount, failedFiles };
}

async function saveCourse() {
  try {
    // 验证表单
    if (!newCourse.name || !newCourse.description || !newCourse.category || !newCourse.difficulty) {
      notificationService.error('表单验证失败', '请填写所有必填字段');
      return;
    }
    
    // 准备提交的数据
    const courseData = {
      name: newCourse.name,
      description: newCourse.description,
      category: newCourse.category,
      difficulty: newCourse.difficulty,
      is_public: newCourse.is_public
    };
    
    console.log('准备提交的课程数据:', courseData);
    
    let response;
    
    if (isEditing.value && currentCourseId.value) {
      // 更新现有课程
      console.log('更新课程:', currentCourseId.value);
      response = await courseAPI.updateCourse(currentCourseId.value, courseData);
      console.log('课程更新成功:', response);
      notificationService.success('课程更新成功', `课程 "${newCourse.name}" 已更新`);
    } else {
      // 创建新课程
      console.log('创建新课程');
      response = await courseAPI.createCourse(courseData);
      console.log('课程创建成功:', response);

      const createdCourse = response as unknown as Course;
      if (createdCourse?.id && newCourseMaterialFiles.value.length > 0) {
        const { uploadedCount, failedFiles } = await uploadInitialMaterials(createdCourse.id, newCourseMaterialFiles.value);
        if (failedFiles.length > 0) {
          notificationService.warning(
            '课程已创建',
            `课程 "${newCourse.name}" 已创建，${uploadedCount} 个资源上传成功，${failedFiles.length} 个资源上传失败`
          );
        } else {
          notificationService.success(
            '课程创建成功',
            `课程 "${newCourse.name}" 已创建，并上传了 ${uploadedCount} 个课件资源`
          );
        }
      } else {
        notificationService.success('课程创建成功', `课程 "${newCourse.name}" 已创建`);
      }
    }
    
    // 关闭模态框
    closeCreateModal();
    
    // 重新加载课程列表
    await fetchCourses();
  } catch (error) {
    console.error(isEditing.value ? '更新课程失败:' : '创建课程失败:', error);
    notificationService.error(
      isEditing.value ? '更新课程失败' : '创建课程失败', 
      '操作未能完成，请重试'
    );
  }
}

async function confirmDeleteCourse(course: Course) {
  const confirmed = await dialogService.warning({
    title: '删除课程',
    message: `确定要删除课程"${course.name}"吗？此操作不可恢复。`,
    confirmText: '删除',
    cancelText: '取消'
  });
  
  if (confirmed) {
    try {
      await courseAPI.deleteCourse(course.id);
      notificationService.success('课程删除成功', `课程 "${course.name}" 已删除`);
      // 重新加载课程列表
      await fetchCourses();
    } catch (error) {
      console.error('删除课程失败:', error);
      const errorMessage = axios.isAxiosError(error)
        ? String(error.response?.data?.message || error.response?.data?.msg || error.message || '').trim()
        : String((error as Error)?.message || '').trim();
      notificationService.error(
        '删除课程失败',
        errorMessage || '操作未能完成，请重试'
      );
    }
  }
}

onBeforeUnmount(() => {
  if (searchTimeout) {
    clearTimeout(searchTimeout);
  }
});
</script> 
