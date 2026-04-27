import { request } from '@/utils'

export default {
  getKnowledgeCategoryList: (params = {}) => request.get('/knowledge/category/list', { params }),
  getKnowledgeCategoryById: (params = {}) => request.get('/knowledge/category/get', { params }),
  createKnowledgeCategory: (data = {}) => request.post('/knowledge/category/create', data),
  updateKnowledgeCategory: (data = {}) => request.post('/knowledge/category/update', data),
  deleteKnowledgeCategory: (params = {}) => request.delete('/knowledge/category/delete', { params }),
  getKnowledgeArticleList: (params = {}) => request.get('/knowledge/article/list', { params }),
  getKnowledgeArticleById: (params = {}) => request.get('/knowledge/article/get', { params }),
  createKnowledgeArticle: (data = {}) => request.post('/knowledge/article/create', data),
  updateKnowledgeArticle: (data = {}) => request.post('/knowledge/article/update', data),
  deleteKnowledgeArticle: (params = {}) => request.delete('/knowledge/article/delete', { params }),
  getPublishedKnowledgeCategoryList: (params = {}) => request.get('/knowledge/published/category/list', { params }),
  getPublishedKnowledgeArticleList: (params = {}) => request.get('/knowledge/published/article/list', { params }),
  getPublishedKnowledgeArticleById: (params = {}) => request.get('/knowledge/published/article/get', { params }),
}
