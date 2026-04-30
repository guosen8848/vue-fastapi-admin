<script setup>
import { h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import {
  NButton,
  NCard,
  NForm,
  NFormItem,
  NInput,
  NModal,
  NPopconfirm,
  NSelect,
  NSwitch,
  NTag,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import QueryBarItem from '@/components/query-bar/QueryBarItem.vue'
import CrudModal from '@/components/table/CrudModal.vue'
import CrudTable from '@/components/table/CrudTable.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import { useCRUD } from '@/composables'
import { formatDate, renderIcon } from '@/utils'

import examApi from '@/api/exam'

defineOptions({ name: '题库管理' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')
const fileInputRef = ref(null)

const importVisible = ref(false)
const importLoading = ref(false)
const importFormRef = ref(null)
const importErrors = ref([])
const importForm = ref({
  name: '',
  desc: '',
  is_active: true,
  file: null,
  file_name: '',
})

const activeOptions = [
  { label: '启用', value: true },
  { label: '停用', value: false },
]

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
  name: '题库',
  initForm: {
    name: '',
    desc: '',
    is_active: true,
  },
  doCreate: examApi.createExamBank,
  doUpdate: examApi.updateExamBank,
  doDelete: examApi.deleteExamBank,
  refresh: () => $table.value?.handleSearch(),
})

const rules = {
  name: [
    {
      required: true,
      message: '请输入题库名称',
      trigger: ['input', 'blur'],
    },
  ],
}

const importRules = {
  name: [
    {
      required: true,
      message: '请输入题库名称',
      trigger: ['input', 'blur'],
    },
  ],
}

onMounted(() => {
  $table.value?.handleSearch()
})

function openAddBank() {
  handleAdd()
}

function openEditBank(row) {
  handleEdit(row)
}

function openImportModal() {
  importVisible.value = true
  importErrors.value = []
  importForm.value = {
    name: '',
    desc: '',
    is_active: true,
    file: null,
    file_name: '',
  }
}

function triggerFileSelect() {
  fileInputRef.value?.click()
}

function handleFileChange(event) {
  const file = event.target?.files?.[0]
  if (!file) return
  importForm.value.file = file
  importForm.value.file_name = file.name
  importErrors.value = []
  event.target.value = ''
}

async function handleDownloadTemplate() {
  const response = await examApi.downloadExamBankTemplate()
  const blob = new Blob([response.data], {
    type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
  })
  const link = document.createElement('a')
  link.href = URL.createObjectURL(blob)
  link.download = 'exam_question_template.xlsx'
  link.click()
  URL.revokeObjectURL(link.href)
}

async function handleImportBank() {
  importFormRef.value?.validate(async (err) => {
    if (err) return
    if (!importForm.value.file) {
      $message.error('请先选择题库文件')
      return
    }

    importLoading.value = true
    try {
      const { data } = await examApi.importExamBank(importForm.value)
      if (!data.success) {
        importErrors.value = Array.isArray(data.errors) ? data.errors : []
        $message.warning(`导入校验失败，共 ${importErrors.value.length} 条问题`)
        return
      }

      importVisible.value = false
      importErrors.value = []
      $message.success(`导入成功，共创建 ${data.question_count} 道题目`)
      $table.value?.handleSearch()
    } finally {
      importLoading.value = false
    }
  })
}

async function handleToggleActive(row) {
  row.publishing = true
  const nextValue = !row.is_active
  try {
    await examApi.updateExamBank({
      id: row.id,
      name: row.name,
      desc: row.desc,
      is_active: nextValue,
    })
    row.is_active = nextValue
    $message.success(nextValue ? '已启用' : '已停用')
    $table.value?.handleSearch()
  } finally {
    row.publishing = false
  }
}

const columns = [
  {
    title: '题库名称',
    key: 'name',
    align: 'center',
    width: 140,
    ellipsis: { tooltip: true },
  },
  {
    title: '题目数量',
    key: 'question_count',
    align: 'center',
    width: 70,
  },
  {
    title: '来源文件',
    key: 'source_file_name',
    align: 'center',
    width: 160,
    ellipsis: { tooltip: true },
    render(row) {
      return h('span', row.source_file_name || '-')
    },
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
    title: '更新时间',
    key: 'updated_at',
    align: 'center',
    width: 120,
    render(row) {
      return h('span', formatDate(row.updated_at, 'YYYY-MM-DD HH:mm:ss'))
    },
  },
  {
    title: '操作',
    key: 'actions',
    align: 'center',
    width: 180,
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
              onClick: () => openEditBank(row),
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/exam/bank/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ bank_id: row.id }),
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
                [[vPermission, 'delete/api/v1/exam/bank/delete']]
              ),
            default: () => h('div', {}, '确定删除该题库吗?'),
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <CommonPage show-footer title="题库管理">
    <template #action>
      <NButton type="default" class="mr-12" @click="handleDownloadTemplate">
        <TheIcon icon="material-symbols:download-rounded" :size="18" class="mr-5" />下载模板
      </NButton>
      <NButton
        v-permission="'post/api/v1/exam/bank/import'"
        type="primary"
        class="mr-12"
        @click="openImportModal"
      >
        <TheIcon icon="material-symbols:upload-file-outline" :size="18" class="mr-5" />导入题库
      </NButton>
      <NButton v-permission="'post/api/v1/exam/bank/create'" type="primary" @click="openAddBank">
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建题库
      </NButton>
    </template>

    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="examApi.getExamBankList"
    >
      <template #queryBar>
        <QueryBarItem label="题库名称">
          <NInput
            v-model:value="queryItems.name"
            clearable
            placeholder="请输入题库名称"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem label="启用状态">
          <NSelect
            v-model:value="queryItems.is_active"
            clearable
            :options="activeOptions"
            placeholder="请选择状态"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      @save="handleSave"
    >
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="80"
        :model="modalForm"
        :rules="rules"
      >
        <NFormItem label="题库名称" path="name">
          <NInput v-model:value="modalForm.name" placeholder="请输入题库名称" />
        </NFormItem>
        <NFormItem label="题库说明" path="desc">
          <NInput
            v-model:value="modalForm.desc"
            type="textarea"
            placeholder="请输入题库说明"
            :autosize="{ minRows: 3, maxRows: 5 }"
          />
        </NFormItem>
        <NFormItem label="启用状态" path="is_active">
          <NSwitch v-model:value="modalForm.is_active" />
        </NFormItem>
      </NForm>
    </CrudModal>

    <NModal
      v-model:show="importVisible"
      preset="card"
      title="导入题库"
      :mask-closable="false"
      style="width: 760px"
    >
      <NForm
        ref="importFormRef"
        label-placement="left"
        label-align="left"
        :label-width="80"
        :model="importForm"
        :rules="importRules"
      >
        <NFormItem label="题库名称" path="name">
          <NInput v-model:value="importForm.name" placeholder="请输入题库名称" />
        </NFormItem>
        <NFormItem label="题库说明" path="desc">
          <NInput
            v-model:value="importForm.desc"
            type="textarea"
            placeholder="请输入题库说明"
            :autosize="{ minRows: 3, maxRows: 5 }"
          />
        </NFormItem>
        <NFormItem label="启用状态" path="is_active">
          <NSwitch v-model:value="importForm.is_active" />
        </NFormItem>
        <NFormItem label="题库文件">
          <div class="exam-bank-upload">
            <NButton type="primary" @click="triggerFileSelect">选择文件</NButton>
            <span>{{ importForm.file_name || '请上传 .xlsx 文件' }}</span>
            <input
              ref="fileInputRef"
              type="file"
              accept=".xlsx"
              hidden
              @change="handleFileChange"
            />
          </div>
        </NFormItem>
      </NForm>

      <NCard v-if="importErrors.length" title="校验结果" size="small" class="mt-12">
        <template #header-extra>
          <NTag type="error">{{ importErrors.length }} 条错误</NTag>
        </template>
        <ul class="exam-bank-error-list">
          <li v-for="(item, index) in importErrors" :key="index">
            第 {{ item.row || '-' }} 行 / {{ item.field }}：{{ item.message }}
          </li>
        </ul>
      </NCard>

      <template #footer>
        <div class="flex justify-end gap-12">
          <NButton @click="importVisible = false">取消</NButton>
          <NButton type="primary" :loading="importLoading" @click="handleImportBank"
            >开始导入</NButton
          >
        </div>
      </template>
    </NModal>
  </CommonPage>
</template>

<style scoped lang="scss">
.exam-bank-upload {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.exam-bank-error-list {
  margin: 0;
  padding-left: 18px;
  color: #c2410c;
  line-height: 1.75;
}
</style>
