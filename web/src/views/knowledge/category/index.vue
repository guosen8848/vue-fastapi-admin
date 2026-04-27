<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import {
  NButton,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NPopconfirm,
  NSwitch,
  NTreeSelect,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'

import { formatDate, renderIcon } from '@/utils'
import { useCRUD } from '@/composables'
import knowledgeApi from '@/api/knowledge'

defineOptions({ name: '知识分类' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

const initForm = {
  parent_id: 0,
  order: 0,
  is_active: true,
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
  name: '知识分类',
  initForm,
  doCreate: knowledgeApi.createKnowledgeCategory,
  doUpdate: knowledgeApi.updateKnowledgeCategory,
  doDelete: knowledgeApi.deleteKnowledgeCategory,
  refresh: () => $table.value?.handleSearch(),
})

const categoryOptions = ref([])

const rules = {
  name: [
    {
      required: true,
      message: '请输入分类名称',
      trigger: ['input', 'blur', 'change'],
    },
  ],
}

onMounted(async () => {
  $table.value?.handleSearch()
  await fetchCategoryOptions()
})

async function fetchCategoryOptions() {
  const { data } = await knowledgeApi.getKnowledgeCategoryList()
  categoryOptions.value = [{ id: 0, name: '根分类', children: data }]
}

function openAddCategory() {
  handleAdd()
}

function openEditCategory(row) {
  handleEdit(row)
}

async function deleteCategory(row) {
  await handleDelete({ category_id: row.id })
  await fetchCategoryOptions()
}

async function handleToggleActive(row) {
  if (!row.id) return
  row.publishing = true
  const nextValue = !row.is_active
  try {
    await knowledgeApi.updateKnowledgeCategory({
      id: row.id,
      name: row.name,
      desc: row.desc,
      order: row.order,
      parent_id: row.parent_id,
      is_active: nextValue,
    })
    row.is_active = nextValue
    $message.success(nextValue ? '已启用' : '已停用')
    await fetchCategoryOptions()
  } finally {
    row.publishing = false
  }
}

const columns = [
  {
    title: '分类名称',
    key: 'name',
    align: 'center',
    width: 120,
    ellipsis: { tooltip: true },
  },
  {
    title: '说明',
    key: 'desc',
    align: 'center',
    width: 180,
    ellipsis: { tooltip: true },
  },
  {
    title: '排序',
    key: 'order',
    align: 'center',
    width: 60,
  },
  {
    title: '启用',
    key: 'is_active',
    align: 'center',
    width: 70,
    render(row) {
      return h(NSwitch, {
        size: 'small',
        rubberBand: false,
        value: row.is_active,
        loading: !!row.publishing,
        onUpdateValue: () => handleToggleActive(row),
      })
    },
  },
  {
    title: '创建时间',
    key: 'created_at',
    align: 'center',
    width: 90,
    render(row) {
      return h('span', formatDate(row.created_at, 'YYYY-MM-DD HH:mm:ss'))
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 130,
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
              onClick: () => openEditCategory(row),
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/knowledge/category/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => deleteCategory(row),
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
                [[vPermission, 'delete/api/v1/knowledge/category/delete']]
              ),
            default: () => h('div', {}, '确定删除该知识分类吗?'),
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <CommonPage show-footer title="知识分类">
    <template #action>
      <NButton
        v-permission="'post/api/v1/knowledge/category/create'"
        type="primary"
        @click="openAddCategory"
      >
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建分类
      </NButton>
    </template>

    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :is-pagination="false"
      :columns="columns"
      :get-data="knowledgeApi.getKnowledgeCategoryList"
    />

    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      @save="handleSave(fetchCategoryOptions)"
    >
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="80"
        :model="modalForm"
        :rules="rules"
      >
        <NFormItem label="上级分类" path="parent_id">
          <NTreeSelect
            v-model:value="modalForm.parent_id"
            :options="categoryOptions"
            key-field="id"
            label-field="name"
            clearable
            default-expand-all
          />
        </NFormItem>
        <NFormItem label="分类名称" path="name">
          <NInput v-model:value="modalForm.name" placeholder="请输入分类名称" />
        </NFormItem>
        <NFormItem label="分类说明" path="desc">
          <NInput v-model:value="modalForm.desc" type="textarea" placeholder="请输入分类说明" />
        </NFormItem>
        <NFormItem label="排序" path="order">
          <NInputNumber v-model:value="modalForm.order" min="0" />
        </NFormItem>
        <NFormItem label="启用状态" path="is_active">
          <NSwitch v-model:value="modalForm.is_active" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>
