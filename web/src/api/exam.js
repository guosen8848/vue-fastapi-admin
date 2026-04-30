import axios from 'axios'

import { getToken, request } from '@/utils'

const fileRequest = axios.create({
  baseURL: import.meta.env.VITE_BASE_API,
  timeout: 12000,
})

fileRequest.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers.token = config.headers.token || token
  }
  return config
})

export default {
  getExamDashboard: () => request.get('/exam/dashboard'),

  getExamBankList: (params = {}) => request.get('/exam/bank/list', { params }),
  getExamBankById: (params = {}) => request.get('/exam/bank/get', { params }),
  createExamBank: (data = {}) => request.post('/exam/bank/create', data),
  updateExamBank: (data = {}) => request.post('/exam/bank/update', data),
  deleteExamBank: (params = {}) => request.delete('/exam/bank/delete', { params }),
  downloadExamBankTemplate: () =>
    fileRequest.get('/exam/bank/template', {
      responseType: 'blob',
    }),
  importExamBank(data) {
    const formData = new FormData()
    formData.append('name', data.name)
    formData.append('desc', data.desc || '')
    formData.append('is_active', data.is_active)
    formData.append('file', data.file)
    return request.post('/exam/bank/import', formData)
  },

  getExamQuestionList: (params = {}) => request.get('/exam/question/list', { params }),
  getExamQuestionById: (params = {}) => request.get('/exam/question/get', { params }),
  createExamQuestion: (data = {}) => request.post('/exam/question/create', data),
  updateExamQuestion: (data = {}) => request.post('/exam/question/update', data),
  deleteExamQuestion: (params = {}) => request.delete('/exam/question/delete', { params }),

  getExamPaperList: (params = {}) => request.get('/exam/paper/list', { params }),
  getExamPaperById: (params = {}) => request.get('/exam/paper/get', { params }),
  getExamPaperAttempts: (params = {}) => request.get('/exam/paper/attempts', { params }),
  createExamPaper: (data = {}) => request.post('/exam/paper/create', data),
  updateExamPaper: (data = {}) => request.post('/exam/paper/update', data),
  deleteExamPaper: (params = {}) => request.delete('/exam/paper/delete', { params }),
  publishExamPaper: (data = {}) => request.post('/exam/paper/publish', data),
  closeExamPaper: (data = {}) => request.post('/exam/paper/close', data),

  getAnswerableExamPaperList: (params = {}) => request.get('/exam/answer/paper/list', { params }),
  getAnswerableExamPaperById: (params = {}) => request.get('/exam/answer/paper/get', { params }),
  startExamAttempt: (data = {}) => request.post('/exam/attempt/start', data),
  saveExamAttempt: (data = {}) => request.post('/exam/attempt/save', data),
  submitExamAttempt: (data = {}) => request.post('/exam/attempt/submit', data),
  getMyExamAttemptList: (params = {}) => request.get('/exam/attempt/my_list', { params }),
  getMyExamAttemptById: (params = {}) => request.get('/exam/attempt/my_get', { params }),

  getExamPracticeBankList: () => request.get('/exam/practice/bank/list'),
  getExamPracticeQuestionList: (params = {}) =>
    request.get('/exam/practice/question/list', { params }),
  startExamPractice: (data = {}) => request.post('/exam/practice/start', data),
  getExamPracticeById: (params = {}) => request.get('/exam/practice/get', { params }),
  getMyExamPracticeList: (params = {}) => request.get('/exam/practice/my_list', { params }),
  answerExamPractice: (data = {}) => request.post('/exam/practice/answer', data),
  finishExamPractice: (data = {}) => request.post('/exam/practice/finish', data),
  retryExamPractice: (data = {}) => request.post('/exam/practice/retry', data),
  deleteExamPractice: (params = {}) => request.delete('/exam/practice/delete', { params }),

  getExamGradingList: (params = {}) => request.get('/exam/grading/list', { params }),
  getExamGradingDetail: (params = {}) => request.get('/exam/grading/get', { params }),
  claimExamGrading: (data = {}) => request.post('/exam/grading/claim', data),
  releaseExamGrading: (data = {}) => request.post('/exam/grading/release', data),
  scoreExamAnswer: (data = {}) => request.post('/exam/grading/score', data),
  completeExamGrading: (data = {}) => request.post('/exam/grading/complete', data),
}
