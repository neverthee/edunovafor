import axios, { type AxiosProgressEvent } from 'axios'
import { API_BASE_URL } from '@/config/api'

// 创建axios实例
const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000, // 增加超时时间到120秒
  headers: {
    'Content-Type': 'application/json',
  },
})

// 请求拦截器
api.interceptors.request.use(
  (config) => {
    // 添加认证token
    const token = localStorage.getItem('token')
    if (token) {
      config.headers.Authorization = `Bearer ${token}`
    }
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
api.interceptors.response.use(
  (response) => {
    return response.data
  },
  (error) => {
    const status = error.response?.status
    const jwtMessage = String(error.response?.data?.msg || error.response?.data?.message || '').toLowerCase()
    const isJwtFailure = status === 401 || (status === 422 && (
      jwtMessage.includes('jwt') ||
      jwtMessage.includes('signature') ||
      jwtMessage.includes('token') ||
      jwtMessage.includes('subject')
    ))

    if (isJwtFailure) {
      // 清除token并跳转到登录页
      localStorage.removeItem('token')
      localStorage.removeItem('auth')
      localStorage.removeItem('user')
      window.location.href = '/login'
    }
    // 返回原始错误对象，保留完整的错误信息
    return Promise.reject(error)
  }
)

// 认证相关API
export const authAPI = {
  login: (credentials: { username: string; password: string }) =>
    api.post('/auth/login', credentials),
  
  register: (userData: {
    username: string
    email: string
    password: string
    full_name: string
    role?: string
  }) => api.post('/auth/register', userData),
  
  getProfile: () => api.get('/auth/profile'),
  
  updateProfile: (data: any) => {
    console.log('调用updateProfile API，数据类型:', typeof data, data instanceof FormData);
    
    // 检查是否是FormData类型（包含头像上传）
    if (data instanceof FormData) {
      // 使用axios直接发送请求，绕过拦截器的Content-Type设置
      const token = localStorage.getItem('token');
      console.log('发送FormData请求');
      
      // 发送请求
      return fetch(`${API_BASE_URL}/auth/profile`, {
        method: 'PUT',
        headers: {
          'Authorization': token ? `Bearer ${token}` : ''
          // 注意：不要设置 Content-Type，让浏览器自动设置
        },
        body: data // 直接使用原始FormData
      })
      .then(response => {
        if (!response.ok) {
          return response.text().then(text => {
            console.error('FormData请求失败:', text);
            throw new Error(text);
          });
        }
        return response.json();
      })
      .then(data => {
        console.log('FormData请求成功:', data);
        return data;
      })
      .catch(error => {
        console.error('FormData请求失败:', error);
        throw error;
      });
    }
    
    console.log('发送JSON请求, 数据:', JSON.stringify(data));
    
    // 直接使用axios实例，确保Content-Type正确设置
    return api.put('/auth/profile', data, {
      headers: {
        'Content-Type': 'application/json'
      }
    })
    .then(response => {
      console.log('JSON请求响应:', response);
      return response;
    })
    .catch(error => {
      console.error('JSON请求失败:', error);
      throw error;
    });
  },
  
  changePassword: (data: { old_password: string; new_password: string }) =>
    api.post('/auth/change-password', data),
}

// 用户管理API
export const userAPI = {
  getUsers: (params?: any) => {
    console.log('调用getUsers API, params:', params);
    return api.get('/admin/users', { params })
      .then((response: any) => {
        console.log('原始API响应:', response);
        // 检查响应格式
        if (response && typeof response === 'object') {
          // 如果直接包含users数组
          if (Array.isArray(response.users)) {
            return response;
          }
          // 如果包含在data中
          else if (response.data && Array.isArray(response.data.users)) {
            return response.data;
          }
          // 如果直接是数组
          else if (Array.isArray(response)) {
            return { users: response, total: response.length };
          }
        }
        // 如果格式不符合预期，返回一个标准格式
        console.warn('API响应格式与预期不符:', response);
        return { users: [], total: 0 };
      })
      .catch(error => {
        console.error('getUsers API错误:', error);
        throw error;
      });
  },
  getUser: (userId: number) => api.get(`/admin/users/${userId}`),
  createUser: (data: any) => api.post('/admin/users', data),
  updateUser: (userId: number, data: any) => api.put(`/admin/users/${userId}`, data),
  deleteUser: (userId: number) => api.delete(`/admin/users/${userId}`),
}

// 课程管理API
export const courseAPI = {
  getCourses: (params?: any) => api.get('/courses', { params }),
  getCourse: (courseId: number) => api.get(`/courses/${courseId}`),
  createCourse: (data: any, coverImage?: File) => {
    if (coverImage) {
      const formData = new FormData()
      formData.append('data', JSON.stringify(data))
      formData.append('cover_image', coverImage)
      return api.post('/courses', formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    } else {
      return api.post('/courses', data)
    }
  },
  updateCourse: (courseId: number, data: any, coverImage?: File) => {
    if (coverImage) {
      const formData = new FormData()
      formData.append('data', JSON.stringify(data))
      formData.append('cover_image', coverImage)
      return api.put(`/courses/${courseId}`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' }
      })
    } else {
      return api.put(`/courses/${courseId}`, data)
    }
  },
  deleteCourse: (courseId: number) => api.delete(`/courses/${courseId}`),
  getMyCourses: () => api.get('/my-courses'),
  enrollCourse: (courseId: number) => api.post(`/enroll/${courseId}`),
  unenrollCourse: (courseId: number) => api.post(`/unenroll/${courseId}`),
  getCourseStudents: (courseId: number) => api.get(`/courses/${courseId}/students`),
  getAvailableStudents: (courseId: number) => api.get(`/courses/${courseId}/available-students`),
  addStudentsToCourse: (courseId: number, studentIds: number[]) => 
    api.post(`/courses/${courseId}/students`, { student_ids: studentIds }),
  removeStudentFromCourse: (courseId: number, studentId: number) => 
    api.delete(`/courses/${courseId}/students/${studentId}`),
  getCourseChapters: (courseId: number) => api.get(`/courses/${courseId}/chapters`),
}

export const teacherClassAPI = {
  getClasses: () => api.get('/teacher-classes'),
  getAvailableStudents: (classId: number, params?: { search?: string }) =>
    api.get(`/teacher-classes/${classId}/available-students`, { params }),
  createClass: (data: { name: string; description?: string; student_ids?: number[] }) =>
    api.post('/teacher-classes', data),
  updateClass: (classId: number, data: { name?: string; description?: string; student_ids?: number[] }) =>
    api.put(`/teacher-classes/${classId}`, data),
  deleteClass: (classId: number) => api.delete(`/teacher-classes/${classId}`),
  addStudents: (classId: number, studentIds: number[]) =>
    api.post(`/teacher-classes/${classId}/students`, { student_ids: studentIds }),
  removeStudent: (classId: number, studentId: number) =>
    api.delete(`/teacher-classes/${classId}/students/${studentId}`),
}

// 课件资源API
export const materialAPI = {
  getMaterials: (courseId: number) => api.get(`/courses/${courseId}/materials`),
  getMaterial: (materialId: number) => api.get(`/materials/${materialId}`),
  uploadMaterial: (courseId: number, formData: FormData) =>
    api.post(`/courses/${courseId}/materials`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    }),
  previewChaptersFromMaterial: (courseId: number, data: any) =>
    api.post(`/courses/${courseId}/chapters/generate-from-material/preview`, data),
  applyChaptersFromMaterial: (courseId: number, data: any) =>
    api.post(`/courses/${courseId}/chapters/generate-from-material/apply`, data),
  updateMaterial: (materialId: number, data: any) =>
    api.put(`/materials/${materialId}`, data),
  deleteMaterial: (materialId: number) => api.delete(`/materials/${materialId}`),
  downloadMaterial: (materialId: number) => {
    const token = localStorage.getItem('token')
    const url = `${API_BASE_URL}/materials/${materialId}/download`
    const link = document.createElement('a')
    link.href = token ? `${url}?token=${token}` : url
    link.target = '_blank'
    link.click()
  },
}

// 评估管理API
export const assessmentAPI = {
  // 获取评估列表
  getAssessments: (courseIdOrParams?: number | string | Record<string, any>, params?: any) => {
    const isParamsOnlyCall =
      courseIdOrParams !== null &&
      typeof courseIdOrParams === 'object' &&
      !Array.isArray(courseIdOrParams);

    const courseId = isParamsOnlyCall ? undefined : courseIdOrParams;
    const queryParams = isParamsOnlyCall ? courseIdOrParams : params;

    return api.get('/assessments', {
      params: {
        ...(queryParams || {}),
        course_id: courseId ?? queryParams?.course_id
      }
    });
  },

  // 获取单个评估
  getAssessment: (assessmentId: number) => {
    return api.get(`/assessments/${assessmentId}`);
  },

  // 获取课程的评估列表
  getCourseAssessments: (courseId: number): Promise<{ assessments: any[]; total: number }> => {
    return api.get(`/courses/${courseId}/assessments`);
  },

  // 创建评估
  createAssessment: (data: any) => {
    return api.post('/assessments', data);
  },

  // 使用AI自动生成评估
  generateAssessmentWithAI: async (data: any) => {
    try {
      console.log('发送评估生成请求:', data);
      
      // 使用更健壮的错误处理方式发送请求
      let response;
      try {
        response = await api.post('/assessments/ai-generate', data, {
          timeout: 200000, // 增加到200秒超时，因为初始请求可能需要更多时间
          headers: {
            'Content-Type': 'application/json',
            'Accept': 'application/json'
          }
        });
        console.log('API原始响应:', response);
      } catch (axiosError: any) {
        console.error('API请求错误:', axiosError);
        
        // 如果有响应但状态码不是2xx
        if (axiosError.response) {
          console.log('错误响应数据:', axiosError.response.data);
          // 尝试从错误响应中提取请求ID
          if (axiosError.response.data && axiosError.response.data.request_id) {
            return { data: axiosError.response.data };
          }
        }
        throw axiosError;
      }
      
      // 确保我们返回的是一个标准格式的响应对象
      if (!response) {
        return { data: null };
      }
      
      // axios 响应拦截器已经返回 response.data，这里统一包装成 { data }
      if (response.data === undefined) {
        console.log('响应中没有data属性，按已解包数据处理');
        return { data: response };
      }
      
      console.log('收到生成响应:', response.data);
      
      // 确保响应格式一致
      if (response && response.data && !response.data.request_id && typeof response.data === 'string') {
        try {
          // 尝试将字符串解析为JSON
          const parsedData = JSON.parse(response.data);
          return { data: parsedData };
        } catch (e) {
          console.error('无法将响应解析为JSON:', e);
        }
      }
      
      return response;
    } catch (error) {
      console.error('AI生成评估请求失败:', error);
      throw error;
    }
  },

  // 查询AI评估生成状态
  getAIGenerationStatus: async (requestId: string) => {
    try {
      console.log('查询生成状态:', requestId);
      const response = await api.get(`/assessments/ai-generate/${requestId}`, {
        timeout: 15000 // 增加到15秒超时，确保获取状态的稳定性
      });
      
      console.log('状态查询原始响应:', response);
      
      // 确保返回标准格式的响应对象
      if (!response) {
        return { data: { status: 'error', message: '无响应' } };
      }
      
      // axios 响应拦截器已经返回 response.data，这里不能再伪造 status，
      // 否则会把后端返回的 success/error 错误改写成 processing。
      if (response.data === undefined) {
        console.log('状态响应中没有data属性，按已解包数据处理');
        return { data: response };
      }
      
      return response;
    } catch (error: any) {
      console.error('查询AI生成状态失败:', error);
      
      // 尝试从错误响应中提取有用信息
      if (error.response && error.response.data) {
        return { data: { 
          status: 'error', 
          message: error.response.data.message || '状态查询失败',
          error: error.message 
        }};
      }
      
      // 返回一个带有错误信息的标准响应对象，而不是抛出异常
      return { data: { 
        status: 'error', 
        message: error.message || '状态查询失败',
        error: '连接服务器失败'
      }};
    }
  },

  // 更新评估
  updateAssessment: (assessmentId: number, data: any) => {
    return api.put(`/assessments/${assessmentId}`, data);
  },

  getPublication: (assessmentId: number) => {
    return api.get(`/assessments/${assessmentId}/publication`);
  },

  updatePublication: (assessmentId: number, data: { action: 'publish' | 'unpublish'; class_ids: number[] }) => {
    return api.put(`/assessments/${assessmentId}/publication`, data);
  },

  importWordQuestion: (formData: FormData) => {
    return api.post('/assessments/import-word-question', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  importImageQuestion: (formData: FormData) => {
    return api.post('/assessments/import-image-question', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },

  // 删除评估
  deleteAssessment: (assessmentId: number) => {
    return api.delete(`/assessments/${assessmentId}`);
  },

  // 提交评估答案
  submitAssessment: (assessmentId: number, data: any) => {
    return api.post(`/assessments/${assessmentId}/submit`, data);
  },

  // 获取我的答案
  getMyAnswers: () => {
    return api.get('/assessments/my-answers');
  },

  // 获取评估的提交记录
  getSubmissionsByAssessment: (assessmentId: number) => {
    return api.get(`/assessments/${assessmentId}/submissions`);
  },

  // 获取评估的提交数量
  getSubmissionCount: (assessmentId: number) => {
    return api.get(`/assessments/${assessmentId}/submission-count`);
  },

  // 获取学生的提交记录
  getSubmissionsByStudent: (studentId: number, params?: any) => {
    return api.get(`/students/${studentId}/submissions`, { params });
  },

  // 获取单个提交记录
  getSubmission: (submissionId: number) => {
    return api.get(`/submissions/${submissionId}`);
  },

  // 评分提交
  gradeSubmission: (submissionId: number, data: any) => {
    return api.post(`/submissions/${submissionId}/grade`, data);
  }
}

// 学习助手API
export const learningAPI = {
  chatWithAssistant: (data: { question: string; course_id?: number }) =>
    api.post('/chat', data),
  getChatHistory: (params?: any) => api.get('/chat/history', { params }),
  generatePractice: (data: any) => api.post('/practice/generate', data),
  submitPractice: (data: any) => api.post('/practice/submit', data),
  getLearningRecords: (params?: any) => api.get('/learning-records', { params }),
  getTeacherDashboardSummary: () => api.get('/teacher-dashboard/summary'),
}

// 管理员API
export const adminAPI = {
  getDashboardOverview: () => api.get('/admin/dashboard/overview'),
  getActivityStats: (params?: any) => api.get('/admin/dashboard/activity', { params }),
  getPerformanceStats: () => api.get('/admin/dashboard/performance'),
  getTopErrors: (params?: any) => api.get('/admin/dashboard/top-errors', { params }),
  getSystemStats: () => api.get('/admin/stats'),
  updateConfig: (data: any) => api.put('/admin/config', data),
}

// RAG和AI功能API
export const ragAiAPI = {
  // 聊天相关API
  chat: (data: { 
    message: string; 
    course_id?: number | string; 
    conversation_id?: string; 
    stream?: boolean; 
    use_rag?: boolean 
  }) => api.post('/rag/chat', data),
  
  // 获取聊天历史
  getChatHistory: (conversationId: string) => 
    api.get('/rag/history', { params: { conversation_id: conversationId } }),
  
  // 获取对话列表
  getConversations: (courseId?: number | string) => 
    api.get('/rag/conversations', { params: { course_id: courseId } }),

  deleteConversation: (conversationId: string) =>
    api.delete(`/rag/conversations/${encodeURIComponent(conversationId)}`),
  
  // 获取模块状态
  getStatus: () => api.get('/rag/status'),
  
  // 知识库相关API
  getKnowledgeBaseStatus: () => api.get('/rag/knowledge-base/status'),
  uploadToKnowledgeBase: (data: any) => api.post('/rag/knowledge-base/upload', data),
  searchKnowledgeBase: (data: { query: string; top_k?: number }) =>
    api.post('/rag/search', data),
  
  // AI生成功能
  generateLessonPlan: (data: {
    outlineType: 'course' | 'class';
    courseId?: number | string;
    chapterId?: number | string;
    gradeSubject: string;
    duration?: string;
    learningObjectives?: string;
    keyPoints?: string;
    studentLevel?: string;
    customStudentLevel?: string;
    activities?: string[];
    teachingStyle?: string;
    assessmentMethods?: string[];
    detailLevel?: number;
    clarifiedRequirement?: {
      teaching_goals: string[];
      knowledge_points: string[];
      duration: string;
      style: string;
      output_targets: string[];
    };
    structuredRequirement?: {
      topic: string;
      knowledge_points: string[];
      teaching_flow: Array<{
        step: number;
        title: string;
        goal: string;
      }>;
      key_points: string[];
      difficult_points: string[];
      student_profile: {
        grade: string;
        foundation: string;
        learning_preference: string;
      };
      style: {
        teaching_style: string;
        interaction_level: string;
        output_preference: string;
      };
    };
    tempFiles?: string[];
    sourceMappings?: Array<{
      filePath: string;
      usage: 'content' | 'format' | 'case' | 'image_asset';
      knowledgePoint: string;
      isRequired: boolean;
    }>;
    selectedKnowledgeItems?: Array<{
      id?: number;
      course_id?: number | null;
      file_path: string;
      purpose?: 'general' | 'lesson_plan' | string;
      status?: 'pending' | 'processing' | 'completed' | 'failed';
      usage?: SourceUsage;
      knowledgePoint?: string;
      isRequired?: boolean;
    }>;
  }): Promise<LessonPlanGenerateResponse> => api.post('/rag/generate-lesson-plan', data, { timeout: 300000 }),

  reviseLessonPlan: (data: {
    conversation_id: string;
    lesson_plan_spec: LessonPlanSpec;
    revision_request: string;
  }): Promise<ReviseLessonPlanResponse> => api.post('/rag/revise-lesson-plan', data, { timeout: 300000 }),

  generateLessonPpt: (data: GenerateLessonPptRequest): Promise<GenerateLessonPptResponse> =>
    api.post('/rag/generate-lesson-ppt', data, { timeout: 300000 }),

  generateLessonDocx: (data: GenerateLessonDocxRequest): Promise<GenerateLessonDocxResponse> =>
    api.post('/rag/generate-lesson-docx', data, { timeout: 300000 }),

  generateLessonGameHtml: (data: GenerateLessonGameHtmlRequest): Promise<GenerateLessonGameHtmlResponse> =>
    api.post('/rag/generate-lesson-game-html', data, { timeout: 300000 }),

  transcribeAudio: (formData: FormData) =>
    api.post('/rag/transcribe-audio', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    }),
  uploadTempKnowledgeFile: (formData: FormData, options: TempKnowledgeUploadRequestOptions = {}) =>
    api.post('/rag/knowledge/upload-temp', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
      timeout: options.timeout ?? 0,
      signal: options.signal,
      onUploadProgress: options.onUploadProgress
    }),

  processTempSources: (data: {
    file_paths: string[];
    source_mappings: Array<{
      file_path: string;
      usage: 'content' | 'format' | 'case' | 'image_asset';
      knowledge_point: string;
      is_required: boolean;
    }>;
  }) => api.post('/rag/process-temp-sources', data),

  summarizeLessonRequirement: (data: {
    conversation_id?: string;
    course_id?: number | string;
    form_snapshot: Record<string, any>;
  }) => api.post('/rag/summarize-lesson-requirement', data),

  structureTeachingElements: (data: {
    conversation_id?: string;
    course_id?: number | string;
    form_snapshot: Record<string, any>;
    requirement_summary?: Record<string, any>;
    source_mappings?: Array<{
      filePath: string;
      usage: 'content' | 'format' | 'case' | 'image_asset';
      knowledgePoint: string;
      isRequired: boolean;
    }>;
  }) => api.post('/rag/structure-teaching-elements', data),
  
  generateCourseContent: (data: any) => api.post('/ai/generate-course-content', data),
  generateAssessment: (data: any) => api.post('/ai/generate-assessment', data),
  autoGradeAnswer: (data: any) => api.post('/ai/auto-grade', data),
  analyzeLearningPattern: (data?: any) => api.post('/ai/analyze-learning-pattern', data),
  recommendResources: (data: any) => api.post('/ai/recommend-resources', data),
}

// 学习分析API
export const analyticsAPI = {
  // 获取学生学习分析数据
  getStudentAnalytics: (studentId: number | string) => 
    api.get(`/analytics/student/${studentId}`),
  
  // 获取课程学习分析数据
  getCourseAnalytics: (courseId: number | string) => 
    api.get(`/analytics/course/${courseId}`),
  
  // 获取AI分析建议
  getAIAnalysis: (data: { studentId?: number | string, courseId?: number | string }) => 
    api.post('/ai/learning-analysis', data)
}

// 健康检查API
export const healthAPI = {
  check: () => api.get('/health'),
}

// RAG知识库API
export const knowledgeBaseAPI = {
  addToKnowledgeBase: (courseId: number, filePath: string, purpose: 'general' | 'lesson_plan' = 'general') =>
    api.post('/rag/knowledge/add', { course_id: courseId, file_path: filePath, purpose }),
  getKnowledgeBaseStatus: (courseId?: number | string) =>
    api.get(courseId ? `/rag/knowledge/status?course_id=${courseId}` : '/rag/knowledge/status'),
  getSupportedFileTypes: () =>
    api.get('/rag/knowledge/supported-types'),
  importExamples: (courseId: number, purpose: 'general' | 'lesson_plan' = 'lesson_plan') =>
    api.post('/rag/knowledge/import-examples', { course_id: courseId, purpose }),
  removeFromKnowledgeBase: (queueId: number) =>
    api.delete('/rag/knowledge/remove', { data: { queue_id: queueId } }),
  clearQueue: (courseId: number) =>
    api.delete('/rag/knowledge/clear-queue', { data: { course_id: courseId } }),
  batchRemove: (queueIds: number[]) =>
    api.delete('/rag/knowledge/batch-remove', { data: { queue_ids: queueIds } }),
}

export interface LessonPlanSpecRequirementSummary {
  topic: string;
  grade_subject: string;
  outline_type: string;
  chapter_title: string;
  duration: string;
  teaching_goals: string[];
  knowledge_points: string[];
  key_points: string[];
  difficult_points: string[];
  student_profile: {
    grade: string;
    foundation: string;
    learning_preference: string;
  };
  style: {
    teaching_style: string;
    interaction_level: string;
    output_preference: string;
  };
  output_targets: string[];
}

export interface LessonPlanSpecSourceNote {
  source_kind: string;
  source_title: string;
  usage: string;
  knowledge_point: string;
  required: boolean;
  note: string;
  snippets: string[];
}

export interface LessonPlanSpecSlide {
  slide_type: string;
  title: string;
  goal: string;
  bullets: string[];
  visual_suggestion: string;
  source_refs: string[];
}

export interface LessonPlanSpecDocSection {
  section_title: string;
  section_goal: string;
  bullets: string[];
  source_refs: string[];
}

export interface LessonPlanSpecGamePlan {
  mode: string;
  title: string;
  objective: string;
  theme: string;
  mechanic: string;
  estimated_minutes: number;
  stages: LessonPlanSpecGameStage[];
  score_rule: LessonPlanSpecGameScoreRule;
  feedback_style: LessonPlanSpecGameFeedbackStyle;
  steps: string[];
  materials: string[];
  source_refs: string[];
}

export interface LessonPlanSpecGameStage {
  id: string;
  name: string;
  goal: string;
  knowledge_tags: string[];
  question_count: number;
  pass_rule: {
    min_correct: number;
    description: string;
  };
  review_refs: string[];
  teacher_tip: string;
}

export interface LessonPlanSpecGameScoreRule {
  base_score: number;
  combo_bonus: number;
  stage_clear_bonus: number;
  time_bonus_enabled: boolean;
}

export interface LessonPlanSpecGameFeedbackStyle {
  success_tone: string;
  retry_tone: string;
  summary_tone: string;
}

export type SourceUsage = 'content' | 'format' | 'case' | 'image_asset';

export interface ProcessedSourceMapping {
  file_path: string;
  file_name: string;
  usage: SourceUsage;
  knowledge_point: string;
  is_required: boolean;
}

export interface ProcessedSourceChunk {
  index?: number;
  slide_index?: number;
  start_ms?: number;
  end_ms?: number;
  text?: string;
  summary?: string;
  importance_score?: number;
}

export interface ProcessedSource {
  kind: 'document' | 'ppt' | 'image' | 'video';
  mapping: ProcessedSourceMapping;
  raw_text: string;
  chunks: ProcessedSourceChunk[];
  summary: string;
  assets: Record<string, any>;
}

export interface KnowledgeBaseStatusItem {
  id: number;
  course_id: number | null;
  file_path: string;
  purpose?: 'general' | 'lesson_plan' | string;
  status: 'pending' | 'processing' | 'completed' | 'failed';
  usage?: SourceUsage | string;
  knowledgePoint?: string;
  isRequired?: boolean | null;
  progress?: number;
  progress_detail?: {
    stage: string;
    message?: string;
  };
  error_message?: string;
  created_at: string | number;
}

export type GenerateLessonPptTheme = 'clean' | 'tech' | 'vivid';

export interface LessonPlanSpec {
  requirement_summary: LessonPlanSpecRequirementSummary;
  source_notes: LessonPlanSpecSourceNote[];
  ppt_outline: LessonPlanSpecSlide[];
  docx_outline: LessonPlanSpecDocSection[];
  game_plan: LessonPlanSpecGamePlan;
}

export interface RevisionMeta {
  version_index: number;
  based_on_version_index?: number | null;
  revision_request: string;
  created_at: number;
}

export interface LessonPlanSourceItem {
  title: string;
  url: string;
  purpose?: string;
  mapping?: {
    usage: 'content' | 'format' | 'case' | 'image_asset';
    knowledge_point: string;
    is_required: boolean;
  };
}

export interface LessonPlanStoredPayload {
  format: string;
  lesson_plan_spec: LessonPlanSpec;
  sources?: LessonPlanSourceItem[];
  revision_meta?: RevisionMeta;
  generated_assets?: {
    word?: number | null;
    ppt?: number | null;
    game?: number | null;
  };
}

export interface LessonPlanGenerateResponse {
  status: 'success' | 'error';
  message?: string;
  conversation_id?: string;
  outline_type?: string;
  selected_chapter?: string;
  lesson_plan_spec?: LessonPlanSpec;
  core_spec?: Record<string, any>;
  sources?: LessonPlanSourceItem[];
  revision_meta?: RevisionMeta;
}

export interface ReviseLessonPlanResponse {
  status: 'success' | 'error';
  message?: string;
  conversation_id?: string;
  lesson_plan_spec?: LessonPlanSpec;
  core_spec?: Record<string, any>;
  sources?: LessonPlanSourceItem[];
  revision_meta?: RevisionMeta;
}

export interface GenerateLessonPptRequest {
  courseId: number;
  lessonPlanSpec: LessonPlanSpec;
  processedSources?: ProcessedSource[];
  gameHtmlMaterialId?: number;
  theme?: GenerateLessonPptTheme;
  useGallery?: boolean;
  conversation_id?: string;
  version_index?: number | null;
}

export interface GenerateLessonDocxRequest {
  courseId: number;
  lessonPlanSpec: LessonPlanSpec;
  coreSpec?: Record<string, any>;
  conversation_id?: string;
  version_index?: number | null;
}

export interface GenerateLessonGameHtmlRequest {
  courseId: number;
  lessonPlanSpec: LessonPlanSpec;
  gamePlan?: LessonPlanSpecGamePlan;
  theme?: GenerateLessonPptTheme;
  conversation_id?: string;
  version_index?: number | null;
}

export interface GenerateLessonPptResponse {
  status: 'success' | 'error';
  message?: string;
  material_id?: number;
  file_path?: string;
  download_url?: string;
  slide_count?: number;
  theme?: GenerateLessonPptTheme;
  image_stats?: {
    teacher_images: number;
    keyframes: number;
    gallery_images: number;
    text_only_slides: number;
  };
  warnings?: string[];
  material?: {
    id: number;
    title: string;
    material_type: string;
    file_path: string;
    file_hash?: string;
    course_id: number;
    created_at?: string;
    updated_at?: string;
    order?: number;
  };
}

export interface GenerateLessonDocxResponse {
  status: 'success' | 'error';
  message?: string;
  material_id?: number;
  file_path?: string;
  download_url?: string;
  section_count?: number;
  material?: {
    id: number;
    title: string;
    material_type: string;
    file_path: string;
    file_hash?: string;
    course_id: number;
    created_at?: string;
    updated_at?: string;
    order?: number;
  };
}

export interface GenerateLessonGameHtmlResponse {
  status: 'success' | 'error';
  message?: string;
  material_id?: number;
  file_path?: string;
  download_url?: string;
  stage_count?: number;
  question_count?: number;
  material?: {
    id: number;
    title: string;
    material_type: string;
    file_path: string;
    file_hash?: string;
    course_id: number;
    created_at?: string;
    updated_at?: string;
    order?: number;
  };
}

export interface TempKnowledgeUploadRequestOptions {
  timeout?: number;
  signal?: AbortSignal;
  onUploadProgress?: (progressEvent: AxiosProgressEvent) => void;
}

export default api

