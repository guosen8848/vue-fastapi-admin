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
  getKnowledgeCategoryList: (params = {}) => request.get('/knowledge/category/list', { params }),
  getKnowledgeCategoryById: (params = {}) => request.get('/knowledge/category/get', { params }),
  createKnowledgeCategory: (data = {}) => request.post('/knowledge/category/create', data),
  updateKnowledgeCategory: (data = {}) => request.post('/knowledge/category/update', data),
  deleteKnowledgeCategory: (params = {}) =>
    request.delete('/knowledge/category/delete', { params }),
  getKnowledgeArticleList: (params = {}) => request.get('/knowledge/article/list', { params }),
  getKnowledgeArticleById: (params = {}) => request.get('/knowledge/article/get', { params }),
  createKnowledgeArticle: (data = {}) => request.post('/knowledge/article/create', data),
  updateKnowledgeArticle: (data = {}) => request.post('/knowledge/article/update', data),
  deleteKnowledgeArticle: (params = {}) => request.delete('/knowledge/article/delete', { params }),
  uploadKnowledgeArticleBlock(file) {
    const formData = new FormData()
    formData.append('file', file)
    return request.post('/knowledge/article/block/upload', formData)
  },
  getKnowledgeArticleBlockFile: (params = {}) =>
    fileRequest.get('/knowledge/article/block/file', {
      params,
      responseType: 'blob',
    }),
  getPublishedKnowledgeCategoryList: (params = {}) =>
    request.get('/knowledge/published/category/list', { params }),
  getPublishedKnowledgeArticleList: (params = {}) =>
    request.get('/knowledge/published/article/list', { params }),
  getPublishedKnowledgeArticleById: (params = {}) =>
    request.get('/knowledge/published/article/get', { params }),
  getPublishedKnowledgeArticleBlockFile: (params = {}) =>
    fileRequest.get('/knowledge/published/article/block/file', {
      params,
      responseType: 'blob',
    }),
}
