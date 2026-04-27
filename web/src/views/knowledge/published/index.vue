<script setup>
import { onMounted, ref } from 'vue'
import { NButton, NEmpty, NInput, NLayout, NLayoutContent, NLayoutSider, NSpin, NTag, NTree } from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import knowledgeApi from '@/api/knowledge'
import { formatDate } from '@/utils'

defineOptions({ name: '知识浏览' })

const treeLoading = ref(false)
const detailLoading = ref(false)

const articleTree = ref([])
const activeArticleId = ref(null)
const articleDetail = ref(null)
const searchTitle = ref('')

onMounted(async () => {
  await loadKnowledgeTree()
})

async function loadKnowledgeTree() {
  treeLoading.value = true
  try {
    const [{ data: categoryTree }, { data: articleList }] = await Promise.all([
      knowledgeApi.getPublishedKnowledgeCategoryList(),
      knowledgeApi.getPublishedKnowledgeArticleList({
        page: 1,
        page_size: 9999,
        title: searchTitle.value || undefined,
      }),
    ])

    articleTree.value = buildTreeOptions(categoryTree, articleList)

    const firstArticleId = findFirstArticleId(articleTree.value)
    if (!firstArticleId) {
      activeArticleId.value = null
      articleDetail.value = null
      return
    }

    await loadArticleDetail(firstArticleId)
  } finally {
    treeLoading.value = false
  }
}

async function handleSearch() {
  await loadKnowledgeTree()
}

async function handleResetSearch() {
  searchTitle.value = ''
  await loadKnowledgeTree()
}

function buildTreeOptions(categoryTree, articleList) {
  const articleMap = {}

  articleList.forEach((article) => {
    if (!articleMap[article.category_id]) {
      articleMap[article.category_id] = []
    }
    articleMap[article.category_id].push(article)
  })

  Object.values(articleMap).forEach((items) => {
    items.sort((a, b) => {
      if (a.is_top !== b.is_top) return Number(b.is_top) - Number(a.is_top)
      return new Date(b.published_at || 0).getTime() - new Date(a.published_at || 0).getTime()
    })
  })

  function buildNodes(categories = []) {
    return categories
      .map((category) => {
        const childCategoryNodes = buildNodes(category.children || [])
        const articleNodes = (articleMap[category.id] || []).map((article) => ({
          key: `article-${article.id}`,
          label: article.title,
          kind: 'article',
          article_id: article.id,
          is_top: article.is_top,
        }))

        const children = [...childCategoryNodes, ...articleNodes]
        if (!children.length) return null

        return {
          key: `category-${category.id}`,
          label: category.display_name || category.name,
          kind: 'category',
          category_id: category.id,
          children,
        }
      })
      .filter(Boolean)
  }

  return buildNodes(categoryTree)
}

function findFirstArticleId(nodes = []) {
  for (const node of nodes) {
    if (node.kind === 'article') {
      return node.article_id
    }
    const childArticleId = findFirstArticleId(node.children || [])
    if (childArticleId) return childArticleId
  }
  return null
}

async function loadArticleDetail(articleId) {
  if (!articleId || activeArticleId.value === articleId) return
  detailLoading.value = true
  try {
    const { data } = await knowledgeApi.getPublishedKnowledgeArticleById({ article_id: articleId })
    articleDetail.value = data
    activeArticleId.value = articleId
  } finally {
    detailLoading.value = false
  }
}

function handleNodeProps({ option }) {
  const classes = ['knowledge-tree-node']

  if (option.kind === 'category') {
    classes.push('knowledge-tree-node-category')
    return {
      class: classes.join(' '),
    }
  }

  classes.push('knowledge-tree-node-article')
  if (option.article_id === activeArticleId.value) {
    classes.push('is-active')
  }

  return {
    class: classes.join(' '),
    onClick() {
      loadArticleDetail(option.article_id)
    },
  }
}

function renderPrefix({ option }) {
  if (option.kind === 'article') {
    return option.is_top ? '★' : '·'
  }
  return ''
}
</script>

<template>
  <NLayout has-sider class="knowledge-browser-layout">
    <NLayoutSider
      bordered
      content-style="padding: 24px 20px;"
      :collapsed-width="0"
      :width="300"
      show-trigger="arrow-circle"
      collapse-mode="width"
      class="knowledge-browser-sider"
    >
      <div class="knowledge-browser-sider-header">
        <h1>知识目录</h1>
        <p>按分类展开并选择已发布文章</p>
      </div>

      <NSpin :show="treeLoading">
        <NEmpty v-if="!articleTree.length" description="暂无可浏览文章" />
        <NTree
          v-else
          block-line
          default-expand-all
          key-field="key"
          label-field="label"
          :data="articleTree"
          :node-props="handleNodeProps"
          :render-prefix="renderPrefix"
        />
      </NSpin>
    </NLayoutSider>

    <NLayoutContent class="knowledge-browser-content">
      <CommonPage show-footer>
        <template #header>
          <div class="knowledge-browser-header">
            <div class="knowledge-browser-search">
              <NInput
                v-model:value="searchTitle"
                clearable
                placeholder="请输入文章标题搜索"
                @keypress.enter="handleSearch"
              />
              <NButton type="primary" @click="handleSearch">搜索</NButton>
              <NButton @click="handleResetSearch">重置</NButton>
            </div>
          </div>
        </template>

        <NSpin :show="detailLoading">
          <NEmpty v-if="!articleDetail" description="请选择左侧文章查看内容" />
          <article v-else class="knowledge-article">
            <header class="knowledge-article-header">
              <div class="knowledge-article-title-wrap">
                <h2>{{ articleDetail.title }}</h2>
                <div class="knowledge-article-meta">
                  <span>分类：{{ articleDetail.category?.name || '-' }}</span>
                  <span>
                    发布时间：{{
                      articleDetail.published_at
                        ? formatDate(articleDetail.published_at, 'YYYY-MM-DD HH:mm:ss')
                        : '-'
                    }}
                  </span>
                </div>
              </div>
              <NTag v-if="articleDetail.is_top" type="warning">置顶</NTag>
            </header>

            <div v-if="articleDetail.tags?.length" class="knowledge-article-tags">
              <NTag v-for="tag in articleDetail.tags" :key="tag" type="info" size="small">
                {{ tag }}
              </NTag>
            </div>

            <div v-if="articleDetail.summary" class="knowledge-article-summary">
              {{ articleDetail.summary }}
            </div>

            <div class="knowledge-article-content">
              {{ articleDetail.content }}
            </div>
          </article>
        </NSpin>
      </CommonPage>
    </NLayoutContent>
  </NLayout>
</template>

<style scoped lang="scss">
.knowledge-browser-layout {
  width: 100%;
  height: 100%;
  min-height: calc(100vh - 120px);
}

.knowledge-browser-sider {
  background: #fff;
}

.knowledge-browser-sider-header {
  margin-bottom: 20px;

  h1 {
    margin: 0;
    font-size: 28px;
    font-weight: 700;
    color: #1f2937;
    line-height: 1.2;
  }

  p {
    margin: 10px 0 0;
    font-size: 13px;
    color: #6b7280;
    line-height: 1.6;
  }
}

.knowledge-browser-content {
  min-width: 0;
}

.knowledge-browser-header {
  display: flex;
  align-items: center;
  justify-content: flex-start;
}

.knowledge-browser-search {
  display: flex;
  align-items: center;
  gap: 10px;
  width: min(560px, 100%);
}

.knowledge-article {
  min-height: 520px;
}

.knowledge-article-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  margin-bottom: 18px;
  padding-bottom: 18px;
  border-bottom: 1px solid #eef2f7;
}

.knowledge-article-title-wrap h2 {
  margin: 0;
  font-size: 28px;
  font-weight: 700;
  line-height: 1.35;
  color: #111827;
}

.knowledge-article-meta {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  margin-top: 12px;
  font-size: 13px;
  color: #6b7280;
}

.knowledge-article-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-bottom: 16px;
}

.knowledge-article-summary {
  margin-bottom: 18px;
  padding: 14px 16px;
  border-radius: 12px;
  background: #f8fafc;
  color: #475569;
  line-height: 1.75;
}

.knowledge-article-content {
  font-size: 15px;
  line-height: 1.95;
  color: #1f2937;
  white-space: pre-wrap;
  word-break: break-word;
}

:deep(.knowledge-tree-node .n-tree-node-content) {
  border-radius: 8px;
  transition: background-color 0.2s ease, color 0.2s ease;
}

:deep(.knowledge-tree-node-category .n-tree-node-content) {
  font-weight: 600;
  color: #374151;
}

:deep(.knowledge-tree-node-article .n-tree-node-content) {
  color: #4b5563;
  cursor: pointer;
}

:deep(.knowledge-tree-node-article .n-tree-node-content:hover) {
  background: #f5f8ff;
  color: #2563eb;
}

:deep(.knowledge-tree-node-article.is-active .n-tree-node-content) {
  background: #eff6ff;
  color: #2563eb;
}

@media (max-width: 960px) {
  .knowledge-browser-layout {
    display: block;
  }

  .knowledge-browser-sider {
    width: 100% !important;
  }

  .knowledge-browser-search {
    width: 100%;
    flex-wrap: wrap;
  }

  .knowledge-article-header {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
