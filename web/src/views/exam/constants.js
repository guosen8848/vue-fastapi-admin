export const QUESTION_OPTION_KEYS = ['A', 'B', 'C', 'D', 'E', 'F']

export const questionTypeOptions = [
  { label: '单选题', value: 'single_choice' },
  { label: '多选题', value: 'multiple_choice' },
  { label: '判断题', value: 'true_false' },
  { label: '填空题', value: 'fill_blank' },
  { label: '简答题', value: 'short_answer' },
]

export const difficultyOptions = [
  { label: '简单', value: 'simple' },
  { label: '中等', value: 'medium' },
  { label: '困难', value: 'hard' },
]

export const paperStatusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
  { label: '已关闭', value: 'closed' },
]

export const attemptStatusOptions = [
  { label: '答题中', value: 'in_progress' },
  { label: '待阅卷', value: 'pending_review' },
  { label: '已阅卷', value: 'graded' },
]

export const judgeStatusOptions = [
  { label: '自动判对', value: 'auto_correct' },
  { label: '自动判错', value: 'auto_wrong' },
  { label: '待人工判题', value: 'manual_pending' },
  { label: '人工判题完成', value: 'manual_done' },
]

export const practiceStatusOptions = [
  { label: '练习中', value: 'in_progress' },
  { label: '已完成', value: 'completed' },
]

export const trueFalseOptions = [
  { label: '正确', value: 'TRUE' },
  { label: '错误', value: 'FALSE' },
]

export const QUESTION_TYPE_LABEL_MAP = questionTypeOptions.reduce((acc, item) => {
  acc[item.value] = item.label
  return acc
}, {})

export const DIFFICULTY_LABEL_MAP = difficultyOptions.reduce((acc, item) => {
  acc[item.value] = item.label
  return acc
}, {})

export const PAPER_STATUS_LABEL_MAP = paperStatusOptions.reduce((acc, item) => {
  acc[item.value] = item.label
  return acc
}, {})

export const ATTEMPT_STATUS_LABEL_MAP = attemptStatusOptions.reduce((acc, item) => {
  acc[item.value] = item.label
  return acc
}, {})

export const JUDGE_STATUS_LABEL_MAP = judgeStatusOptions.reduce((acc, item) => {
  acc[item.value] = item.label
  return acc
}, {})

export const PRACTICE_STATUS_LABEL_MAP = practiceStatusOptions.reduce((acc, item) => {
  acc[item.value] = item.label
  return acc
}, {})

export function createChoiceOptionRows() {
  return QUESTION_OPTION_KEYS.map((optionKey) => ({
    option_key: optionKey,
    option_content: '',
  }))
}

export function isChoiceQuestion(questionType) {
  return ['single_choice', 'multiple_choice'].includes(questionType)
}

export function isSubjectiveQuestion(questionType) {
  return ['fill_blank', 'short_answer'].includes(questionType)
}

export function isObjectiveQuestion(questionType) {
  return ['single_choice', 'multiple_choice', 'true_false'].includes(questionType)
}
