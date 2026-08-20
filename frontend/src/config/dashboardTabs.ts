export interface DashboardTab {
  id: string
  name: string
}

export const studentTabs: DashboardTab[] = [
  { id: 'dashboard', name: '首页' },
  { id: 'my-courses', name: '我的课程' },
  { id: 'courses', name: '课程目录' },
  { id: 'assessments', name: '待办任务' },
  { id: 'analytics', name: '学习分析' },
  { id: 'ai-assistant', name: '智能助手' },
  { id: 'ai-quiz', name: 'AI自测测验' },
  { id: 'knowledge-base', name: '知识库' }
]

export const teacherTabs: DashboardTab[] = [
  { id: 'dashboard', name: '工作台' },
  { id: 'lesson-planner', name: '智能备课' },
  { id: 'assessments', name: '评估测试' },
  { id: 'analytics', name: '学情分析' },
  { id: 'courses', name: '我的课程' },
  { id: 'my-classes', name: '我的班级' },
  { id: 'ai-assistant', name: '智能助手' },
  { id: 'knowledge-base', name: '知识库' }
]

export const adminTabs: DashboardTab[] = [
  { id: 'dashboard', name: '概览' },
  { id: 'admin-dashboard', name: '用户管理' },
  { id: 'courses', name: '课程管理' },
  { id: 'assessments', name: '评估管理' },
  { id: 'settings', name: '系统设置' }
]

export const defaultTabsByRouteName: Record<string, DashboardTab[]> = {
  student: studentTabs,
  teacher: teacherTabs,
  admin: adminTabs
}

export const defaultActiveTabByRouteName: Record<string, string> = {
  student: 'dashboard',
  teacher: 'dashboard',
  admin: 'dashboard'
}
