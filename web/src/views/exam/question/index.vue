<script setup>
import { computed, h, onMounted, ref, resolveDirective, withDirectives } from 'vue'
import {
  NButton,
  NDynamicTags,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
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

import {
  createChoiceOptionRows,
  difficultyOptions,
  DIFFICULTY_LABEL_MAP,
  isChoiceQuestion,
  QUESTION_TYPE_LABEL_MAP,
  questionTypeOptions,
  trueFalseOptions,
} from '../constants'

defineOptions({ name: '题目管理' })

const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

const bankOptions = ref([])
const activeOptions = [
  { label: '启用', value: true },
  { label: '停用', value: false },
]

const initForm = {
  bank_id: null,
  question_type: 'single_choice',
  category_path: '',
  stem: '',
  options: createChoiceOptionRows(),
  correct_answer: [],
  reference_answer: '',
  analysis: '',
  tags: [],
  difficulty: 'medium',
  default_score: 5,
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
  name: '题目',
  initForm,
  doCreate: (payload) => examApi.createExamQuestion(formatQuestionPayload(payload)),
  doUpdate: (payload) => examApi.updateExamQuestion(formatQuestionPayload(payload)),
  doDelete: examApi.deleteExamQuestion,
  refresh: () => $table.value?.handleSearch(),
})

const isChoiceType = computed(() => isChoiceQuestion(modalForm.value.question_type))
const isTrueFalseType = computed(() => modalForm.value.question_type === 'true_false')

const rules = {
  bank_id: [
    {
      required: true,
      type: 'number',
      message: '请选择所属题库',
      trigger: ['change', 'blur'],
    },
  ],
  question_type: [
    {
      required: true,
      message: '请选择题型',
      trigger: ['change', 'blur'],
    },
  ],
  stem: [
    {
      required: true,
      message: '请输入题干',
      trigger: ['input', 'blur'],
    },
  ],
  default_score: [
    {
      required: true,
      type: 'number',
      message: '请输入题目分值',
      trigger: ['change', 'blur'],
    },
  ],
}

onMounted(async () => {
  $table.value?.handleSearch()
  await fetchBanks()
})

async function fetchBanks() {
  const { data } = await examApi.getExamBankList({ page: 1, page_size: 9999 })
  bankOptions.value = data.map((item) => ({
    label: item.name,
    value: item.id,
    is_active: item.is_active,
  }))
}

function resetQuestionTypeFields(questionType) {
  if (questionType === 'single_choice') {
    modalForm.value.options = createChoiceOptionRows()
    modalForm.value.correct_answer = []
    return
  }
  if (questionType === 'multiple_choice') {
    modalForm.value.options = createChoiceOptionRows()
    modalForm.value.correct_answer = []
    return
  }
  if (questionType === 'true_false') {
    modalForm.value.options = []
    modalForm.value.correct_answer = []
    return
  }
  modalForm.value.options = []
  modalForm.value.correct_answer = []
}

function openAddQuestion() {
  handleAdd()
  modalForm.value.tags = []
  modalForm.value.options = createChoiceOptionRows()
  modalForm.value.correct_answer = []
}

async function openEditQuestion(row) {
  const { data } = await examApi.getExamQuestionById({ question_id: row.id })
  handleEdit(normalizeQuestionDetail(data))
}

function normalizeQuestionDetail(data) {
  const optionMap = new Map(
    (data.options || []).map((item) => [item.option_key, item.option_content])
  )
  const options = createChoiceOptionRows().map((item) => ({
    option_key: item.option_key,
    option_content: optionMap.get(item.option_key) || '',
  }))

  return {
    ...data,
    options: isChoiceQuestion(data.question_type) ? options : [],
    correct_answer:
      data.question_type === 'single_choice'
        ? data.correct_answer?.[0] || null
        : Array.isArray(data.correct_answer)
        ? [...data.correct_answer]
        : [],
    tags: Array.isArray(data.tags) ? [...data.tags] : [],
  }
}

function formatQuestionPayload(form) {
  const payload = {
    bank_id: form.bank_id,
    question_type: form.question_type,
    category_path: form.category_path || '',
    stem: form.stem,
    options: [],
    correct_answer: [],
    reference_answer: form.reference_answer || '',
    analysis: form.analysis || '',
    tags: Array.isArray(form.tags) ? [...form.tags] : [],
    difficulty: form.difficulty,
    default_score: Number(form.default_score || 0),
    is_active: !!form.is_active,
  }

  if (form.question_type === 'single_choice') {
    payload.options = (form.options || []).filter((item) => item.option_content?.trim())
    payload.correct_answer = form.correct_answer ? [form.correct_answer] : []
  } else if (form.question_type === 'multiple_choice') {
    payload.options = (form.options || []).filter((item) => item.option_content?.trim())
    payload.correct_answer = Array.isArray(form.correct_answer) ? [...form.correct_answer] : []
  } else if (form.question_type === 'true_false') {
    payload.correct_answer = form.correct_answer ? [form.correct_answer] : []
  }

  if (form.id) {
    payload.id = form.id
  }
  return payload
}

function getChoiceOptions() {
  return (modalForm.value.options || [])
    .filter((item) => item.option_content?.trim())
    .map((item) => ({
      label: `${item.option_key}. ${item.option_content}`,
      value: item.option_key,
    }))
}

async function handleToggleActive(row) {
  row.publishing = true
  try {
    const nextValue = !row.is_active
    const payload = formatQuestionPayload(normalizeQuestionDetail({ ...row, is_active: nextValue }))
    await examApi.updateExamQuestion(payload)
    row.is_active = nextValue
    $message.success(row.is_active ? '已启用' : '已停用')
    $table.value?.handleSearch()
  } finally {
    row.publishing = false
  }
}

function renderQuestionType(questionType) {
  return h(
    NTag,
    { type: 'info' },
    { default: () => QUESTION_TYPE_LABEL_MAP[questionType] || questionType }
  )
}

function renderDifficulty(difficulty) {
  const type = difficulty === 'hard' ? 'error' : difficulty === 'simple' ? 'success' : 'warning'
  return h(NTag, { type }, { default: () => DIFFICULTY_LABEL_MAP[difficulty] || difficulty })
}

const columns = [
  {
    title: '题干',
    key: 'stem',
    align: 'center',
    width: 260,
    ellipsis: { tooltip: true },
  },
  {
    title: '题库',
    key: 'bank_name',
    align: 'center',
    width: 120,
    ellipsis: { tooltip: true },
  },
  {
    title: '题型',
    key: 'question_type',
    align: 'center',
    width: 80,
    render(row) {
      return renderQuestionType(row.question_type)
    },
  },
  {
    title: '难度',
    key: 'difficulty',
    align: 'center',
    width: 80,
    render(row) {
      return renderDifficulty(row.difficulty)
    },
  },
  {
    title: '分值',
    key: 'default_score',
    align: 'center',
    width: 70,
  },
  {
    title: '状态',
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
    title: '被引用',
    key: 'referenced',
    align: 'center',
    width: 70,
    render(row) {
      return h(
        NTag,
        { type: row.referenced ? 'warning' : 'default' },
        { default: () => (row.referenced ? '是' : '否') }
      )
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
              onClick: () => openEditQuestion(row),
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/exam/question/update']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ question_id: row.id }),
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
                [[vPermission, 'delete/api/v1/exam/question/delete']]
              ),
            default: () => h('div', {}, '确定删除该题目吗?'),
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <CommonPage show-footer title="题目管理">
    <template #action>
      <NButton
        v-permission="'post/api/v1/exam/question/create'"
        type="primary"
        @click="openAddQuestion"
      >
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建题目
      </NButton>
    </template>

    <CrudTable
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="examApi.getExamQuestionList"
      :scroll-x="1280"
    >
      <template #queryBar>
        <QueryBarItem label="题库">
          <NSelect
            v-model:value="queryItems.bank_id"
            clearable
            :options="bankOptions"
            placeholder="请选择题库"
          />
        </QueryBarItem>
        <QueryBarItem label="题型">
          <NSelect
            v-model:value="queryItems.question_type"
            clearable
            :options="questionTypeOptions"
            placeholder="请选择题型"
          />
        </QueryBarItem>
        <QueryBarItem label="难度">
          <NSelect
            v-model:value="queryItems.difficulty"
            clearable
            :options="difficultyOptions"
            placeholder="请选择难度"
          />
        </QueryBarItem>
        <QueryBarItem label="状态">
          <NSelect
            v-model:value="queryItems.is_active"
            clearable
            :options="activeOptions"
            placeholder="请选择状态"
          />
        </QueryBarItem>
        <QueryBarItem label="题干">
          <NInput
            v-model:value="queryItems.stem"
            clearable
            placeholder="请输入题干关键字"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
      </template>
    </CrudTable>

    <CrudModal
      v-model:visible="modalVisible"
      :title="modalTitle"
      :loading="modalLoading"
      style="width: 920px"
      @save="handleSave"
    >
      <NForm
        ref="modalFormRef"
        label-placement="left"
        label-align="left"
        :label-width="90"
        :model="modalForm"
        :rules="rules"
      >
        <NFormItem label="所属题库" path="bank_id">
          <NSelect
            v-model:value="modalForm.bank_id"
            :options="bankOptions"
            placeholder="请选择所属题库"
          />
        </NFormItem>
        <NFormItem label="题型" path="question_type">
          <NSelect
            v-model:value="modalForm.question_type"
            :options="questionTypeOptions"
            placeholder="请选择题型"
            @update:value="resetQuestionTypeFields"
          />
        </NFormItem>
        <NFormItem label="题目分类" path="category_path">
          <NInput v-model:value="modalForm.category_path" placeholder="如：Python/基础" />
        </NFormItem>
        <NFormItem label="题干" path="stem">
          <NInput
            v-model:value="modalForm.stem"
            type="textarea"
            placeholder="请输入题干"
            :autosize="{ minRows: 3, maxRows: 5 }"
          />
        </NFormItem>

        <template v-if="isChoiceType">
          <NFormItem label="选项配置">
            <div class="exam-option-grid">
              <div
                v-for="item in modalForm.options"
                :key="item.option_key"
                class="exam-option-item"
              >
                <span>{{ item.option_key }}</span>
                <NInput
                  v-model:value="item.option_content"
                  :placeholder="`请输入选项 ${item.option_key}`"
                />
              </div>
            </div>
          </NFormItem>
        </template>

        <NFormItem v-if="modalForm.question_type === 'single_choice'" label="正确答案">
          <NSelect
            v-model:value="modalForm.correct_answer"
            :options="getChoiceOptions()"
            clearable
            placeholder="请选择正确答案"
          />
        </NFormItem>

        <NFormItem v-if="modalForm.question_type === 'multiple_choice'" label="正确答案">
          <NSelect
            v-model:value="modalForm.correct_answer"
            :options="getChoiceOptions()"
            clearable
            multiple
            placeholder="请选择正确答案"
          />
        </NFormItem>

        <NFormItem v-if="isTrueFalseType" label="正确答案">
          <NSelect
            v-model:value="modalForm.correct_answer"
            :options="trueFalseOptions"
            clearable
            placeholder="请选择正确答案"
          />
        </NFormItem>

        <NFormItem label="参考答案" path="reference_answer">
          <NInput
            v-model:value="modalForm.reference_answer"
            type="textarea"
            placeholder="主观题建议填写参考答案"
            :autosize="{ minRows: 3, maxRows: 5 }"
          />
        </NFormItem>
        <NFormItem label="题目解析" path="analysis">
          <NInput
            v-model:value="modalForm.analysis"
            type="textarea"
            placeholder="请输入题目解析"
            :autosize="{ minRows: 3, maxRows: 5 }"
          />
        </NFormItem>
        <NFormItem label="题目标签" path="tags">
          <NDynamicTags v-model:value="modalForm.tags" />
        </NFormItem>
        <NFormItem label="难度" path="difficulty">
          <NSelect
            v-model:value="modalForm.difficulty"
            :options="difficultyOptions"
            placeholder="请选择难度"
          />
        </NFormItem>
        <NFormItem label="题目分值" path="default_score">
          <NInputNumber v-model:value="modalForm.default_score" :min="1" :precision="2" />
        </NFormItem>
        <NFormItem label="启用状态" path="is_active">
          <NSwitch v-model:value="modalForm.is_active" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </CommonPage>
</template>

<style scoped lang="scss">
.exam-option-grid {
  display: grid;
  width: 100%;
  grid-template-columns: 1fr 1fr;
  gap: 12px;
}

.exam-option-item {
  display: grid;
  grid-template-columns: 32px 1fr;
  align-items: center;
  gap: 10px;
}

@media (max-width: 900px) {
  .exam-option-grid {
    grid-template-columns: 1fr;
  }
}
</style>
