<script setup>
import { computed, h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import {
  NButton,
  NDynamicTags,
  NForm,
  NFormItem,
  NInput,
  NPopconfirm,
  NSelect,
  NSwitch,
  NTag,
  NTreeSelect,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import { useUserStore } from '@/store'
import knowledgeApi from '@/api/knowledge'

import ArticleBlockEditor from '../components/ArticleBlockEditor.vue'
import { normalizeBlocks, stripBlockClientFields } from '../utils/blocks'

defineOptions({ name: '知识文章' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')
const userStore = useUserStore()

const isAdmin = computed(() => {
  return userStore.isSuperUser || userStore.role.some((role) => (role.name || role) === '管理员')
})

const initForm = {
  title: '',
  category_id: null,
  summary: '',
  content: '',
  blocks: [],
  tags: [],
  status: 'draft',
  is_top: false,
}

const {
  modalVisible,
  modalTitle,
  modalLoading,
  handleSave,
  modalForm,
  modalFormRef,
  handleEdit,
  handleDelete,
  handleAdd,
} = useCRUD({
  name: '知识文章',
  initForm,
  doCreate: (payload) => knowledgeApi.createKnowledgeArticle(formatArticlePayload(payload)),
  doUpdate: (payload) => knowledgeApi.updateKnowledgeArticle(formatArticlePayload(payload)),
  doDelete: knowledgeApi.deleteKnowledgeArticle,
  refresh: () => $table.value?.handleSearch(),
})

const categoryOptions = ref([])
const statusOptions = [
  { label: '草稿', value: 'draft' },
  { label: '已发布', value: 'published' },
]

const modalBlockSummary = computed(() => {
  const blocks = modalForm.value.blocks || []
  const fileCount = blocks.filter((block) => block.block_type !== 'text').length
  return `当前共 ${fileCount} 个文件块`
})

const rules = {
  title: [
    {
      required: true,
      message: '请输入文章标题',
      trigger: ['input', 'blur', 'change'],
    },
  ],
  category_id: [
    {
      required: true,
      type: 'number',
      message: '请选择所属分类',
      trigger: ['blur', 'change'],
    },
  ],
  blocks: [
    {
      required: true,
      trigger: ['change', 'blur'],
      validator(_rule, value) {
        if (!Array.isArray(value) || !value.length) {
          return new Error('请至少上传一个文件')
        }

        return true
      },
    },
  ],
}

onMounted(async () => {
  $table.value?.handleSearch()
  await fetchCategories()
})

async function fetchCategories() {
  const { data } = await knowledgeApi.getKnowledgeCategoryList()
  categoryOptions.value = data
}

function formatArticlePayload(form) {
  const payload = {
    title: form.title,
    category_id: form.category_id,
    summary: form.summary || '',
    content: '',
    tags: Array.isArray(form.tags) ? [...form.tags] : [],
    status: form.status,
    is_top: isAdmin.value ? !!form.is_top : false,
    blocks: stripBlockClientFields(form.blocks || []),
  }

  if (form.id) {
    payload.id = form.id
  }

  return payload
}

function normalizeArticlePayload(row, overrides = {}) {
  return {
    id: row.id,
    title: row.title,
    category_id: row.category_id,
    summary: row.summary || '',
    content: row.content || '',
    tags: Array.isArray(row.tags) ? row.tags : [],
    status: row.status,
    is_top: row.is_top,
    ...overrides,
  }
}

function openAddArticle() {
  handleAdd()
  modalForm.value.tags = []
  modalForm.value.blocks = []
}

async function openEditArticle(row) {
  const { data } = await knowledgeApi.getKnowledgeArticleById({ article_id: row.id })
  handleEdit(data)
  modalForm.value.tags = Array.isArray(data.tags) ? [...data.tags] : []
  modalForm.value.blocks = normalizeBlocks(data.blocks || [])
  delete modalForm.value.category
}

async function handleToggleTop(row, value) {
  row.publishing = true
  try {
    await knowledgeApi.updateKnowledgeArticle(normalizeArticlePayload(row, { is_top: value }))
    row.is_top = value
    $message.success(value ? '已置顶' : '已取消置顶')
    $table.value?.handleSearch()
  } finally {
    row.publishing = false
  }
}

async function handleToggleStatus(row) {
  row.publishing = true
  const nextStatus = row.status === 'published' ? 'draft' : 'published'
  try {
    await knowledgeApi.updateKnowledgeArticle(normalizeArticlePayload(row, { status: nextStatus }))
    row.status = nextStatus
    $message.success(nextStatus === 'published' ? '发布成功' : '已转为草稿')
    $table.value?.handleSearch()
  } finally {
    row.publishing = false
  }
}

function renderStatus(status) {
  const type = status === 'published' ? 'success' : 'warning'
  const text = status === 'published' ? '已发布' : '草稿'
  return h(NTag, { type }, { default: () => text })
}

const columns = [
  {
    title: '标题',
    key: 'title',
    align: 'center',
    width: 180,
    ellipsis: { tooltip: true },
  },
  {
    title: '分类',
    key: 'category.name',
    align: 'center',
    width: 100,
    ellipsis: { tooltip: true },
    render(row) {
      return h('span', row.category?.name || '-')
    },
  },
  {
    title: '发布人',
    key: 'publisher.username',
    align: 'center',
    width: 90,
    ellipsis: { tooltip: true },
    render(row) {
      return h('span', row.publisher?.alias || row.publisher?.username || '-')
    },
  },
  {
    title: '状态',
    key: 'status',
    align: 'center',
    width: 80,
    render(row) {
      return renderStatus(row.status)
    },
  },
  {
    title: '置顶',
    key: 'is_top',
    align: 'center',
    width: 70,
    render(row) {
      if (!isAdmin.value) {
        return h(
          NTag,
          { type: row.is_top ? 'warning' : 'default', size: 'small' },
          {
            default: () => (row.is_top ? '是' : '否'),
          }
        )
      }
      return h(NSwitch, {
        size: 'small',
        rubberBand: false,
        value: row.is_top,
        loading: !!row.publishing,
        onUpdateValue: (value) => handleToggleTop(row, value),
      })
    },
  },
  {
    title: '发布时间',
    key: 'published_at',
    align: 'center',
    width: 110,
    render(row) {
      return h('span', row.published_at ? formatDate(row.published_at, 'YYYY-MM-DD HH:mm:ss') : '-')
    },
  },
  {
    title: '更新时间',
    key: 'updated_at',
    align: 'center',
    width: 110,
    render(row) {
      return h('span', formatDate(row.updated_at, 'YYYY-MM-DD HH:mm:ss'))
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 180,
    align: 'center',
    fixed: 'right',
    render(row) {
      return [
        withDirectives(
          h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              type: 'primary',
              onClick: () => openEditArticle(row),
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/knowledge/article/update']]
        ),
        withDirectives(
          h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              type: row.status === 'published' ? 'warning' : 'success',
              onClick: () => handleToggleStatus(row),
            },
            {
              default: () => (row.status === 'published' ? '转草稿' : '发布'),
              icon: renderIcon('material-symbols:publish-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/knowledge/article/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ article_id: row.id }),
          },
          {
            trigger: () =>
              withDirectives(
                h(
                  NButton,
                  {
                    size: 'small',
                    quaternary: true,
                    type: 'error',
                  },
                  {
                    default: () => '删除',
                    icon: renderIcon('material-symbols:delete-outline', { size: 16 }),
                  }
                ),
                [[vPermission, 'delete/api/v1/knowledge/article/delete']]
              ),
            default: () => h('div', {}, '确定删除该知识文章吗?'),
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <CommonPage show-footer title="知识文章">
    <template #action>
      <NButton
        v-permission="'post/api/v1/knowledge/article/create'"
        type="primary"
        @click="openAddArticle"
      >
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建文章
      </NButton>
    </template>

    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="knowledgeApi.getKnowledgeArticleList"
    >
      <template #queryBar>
        <QueryBarItem label="标题" :label-width="40">
          <NInput
            v-model:value="queryItems.title"
            clearable
            type="text"
            placeholder="请输入文章标题"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem label="分类" :label-width="40">
          <NTreeSelect
            v-model:value="queryItems.category_id"
            :options="categoryOptions"
            key-field="id"
            label-field="name"
            clearable
            default-expand-all
            placeholder="请选择分类"
          />
        </QueryBarItem>
        <QueryBarItem label="状态" :label-width="40">
          <NSelect
            v-model:value="queryItems.status"
            clearable
            :options="statusOptions"
            placeholder="请选择状态"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <CrudModal
      v-model:visible="modalVisible"
      width="1100px"
      :title="modalTitle"
      :loading="modalLoading"
      @save="handleSave"
    >
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="88"
        :model="modalForm"
        :rules="rules"
      >
        <NFormItem label="文章标题" path="title">
          <NInput v-model:value="modalForm.title" placeholder="请输入文章标题" />
        </NFormItem>
        <NFormItem label="所属分类" path="category_id">
          <NTreeSelect
            v-model:value="modalForm.category_id"
            :options="categoryOptions"
            key-field="id"
            label-field="name"
            clearable
            default-expand-all
            placeholder="请选择所属分类"
          />
        </NFormItem>
        <NFormItem label="文章摘要" path="summary">
          <NInput
            v-model:value="modalForm.summary"
            type="textarea"
            placeholder="请输入文章摘要"
            :autosize="{ minRows: 2, maxRows: 4 }"
          />
        </NFormItem>
        <NFormItem label="文章标签" path="tags">
          <NDynamicTags v-model:value="modalForm.tags" />
        </NFormItem>
        <NFormItem label="文章状态" path="status">
          <NSelect
            v-model:value="modalForm.status"
            :options="statusOptions"
            placeholder="请选择状态"
          />
        </NFormItem>
        <NFormItem v-if="isAdmin" label="是否置顶" path="is_top">
          <NSwitch v-model:value="modalForm.is_top" />
        </NFormItem>
        <NFormItem label="内容块" path="blocks">
          <div class="article-form-blocks">
            <div class="article-form-blocks-summary">{{ modalBlockSummary }}</div>
            <ArticleBlockEditor v-model="modalForm.blocks" />
          </div>
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>

<style scoped lang="scss">
.article-form-blocks {
  width: 100%;
}

.article-form-blocks-summary {
  margin-bottom: 10px;
  font-size: 13px;
  color: var(--n-text-color-2, #64748b);
}
</style>
