export const LESSON_PLANNER_DRAFT_KEY = 'lessonPlannerDraft'
export const LESSON_PLANNER_RESULT_KEY = 'lessonPlannerResult'
export const LESSON_PLANNER_CONVERSATION_KEY = 'lessonPlannerConversationId'
export const LESSON_PLANNER_STRUCTURED_KEY = 'lessonPlannerStructuredRequirement'
export const LESSON_PLANNER_GAME_EXPORT_KEY = 'lessonPlannerLatestGameHtmlExport'

export function clearLessonPlannerStorage() {
  localStorage.removeItem(LESSON_PLANNER_DRAFT_KEY)
  localStorage.removeItem(LESSON_PLANNER_RESULT_KEY)
  localStorage.removeItem(LESSON_PLANNER_CONVERSATION_KEY)
  localStorage.removeItem(LESSON_PLANNER_STRUCTURED_KEY)
  localStorage.removeItem(LESSON_PLANNER_GAME_EXPORT_KEY)
}
