<script setup>
import { computed, h, nextTick, onMounted, ref, resolveDirective, watch, withDirectives } from 'vue'
import {
  NButton,
  NDataTable,
  NForm,
  NFormItem,
  NInput,
  NInputNumber,
  NModal,
  NPopconfirm,
  NSelect,
  NSpin,
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
import { useAppStore } from '@/store'

import examApi from '@/api/exam'

import {
  ATTEMPT_STATUS_LABEL_MAP,
  DIFFICULTY_LABEL_MAP,
  PAPER_STATUS_LABEL_MAP,
  QUESTION_TYPE_LABEL_MAP,
  attemptStatusOptions,
  difficultyOptions,
  paperStatusOptions,
  questionTypeOptions,
} from '../constants'

defineOptions({ name: '试卷管理' })

const appStore = useAppStore()
const $table = ref(null)
const queryItems = ref({})
const vPermission = resolveDirective('permission')

const bankOptions = ref([])
const selectorVisible = ref(false)
const selectorLoading = ref(false)
const selectorRows = ref([])
const selectorCheckedRowKeys = ref([])
const selectorCheckedRows = ref([])
const selectorRandomCount = ref(1)
const reportLoading = ref(false)
const activeReport = ref(null)
const selectorQuery = ref({
  bank_id: null,
  question_type: null,
  difficulty: null,
  stem: '',
})

const activeOptions = [
  { label: '启用', value: true },
  { label: '停用', value: false },
]

const passFilterOptions = [
  { label: '及格', value: true },
  { label: '未及格', value: false },
]

const reportQuery = ref({
  username: '',
  status: null,
  passed: null,
})

const initForm = {
  title: '',
  desc: '',
  status: 'draft',
  duration_minutes: 0,
  pass_score: 0,
  is_active: true,
  questions: [],
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
  name: '试卷',
  initForm,
  doCreate: (payload) => examApi.createExamPaper(formatPaperPayload(payload)),
  doUpdate: (payload) => examApi.updateExamPaper(formatPaperPayload(payload)),
  doDelete: examApi.deleteExamPaper,
  refresh: () => $table.value?.handleSearch(),
})

const rules = {
  title: [
    {
      required: true,
      message: '请输入试卷标题',
      trigger: ['input', 'blur'],
    },
  ],
}

onMounted(async () => {
  $table.value?.handleSearch()
  await fetchBanks()
})

const questionTotalScore = computed(() =>
  Number(
    (modalForm.value.questions || [])
      .reduce((total, item) => total + Number(item.score || 0), 0)
      .toFixed(2)
  )
)

const selectorRandomAvailableCount = computed(() => {
  const selectedIds = new Set((selectorCheckedRowKeys.value || []).map((item) => Number(item)))
  return (selectorRows.value || []).filter((item) => !selectedIds.has(Number(item.id))).length
})

const reportSummaryItems = computed(() => {
  const summary = activeReport.value?.summary || {}
  return [
    { label: '作答人数', value: summary.attempt_count || 0 },
    { label: '已提交', value: summary.submitted_count || 0 },
    { label: '待阅卷', value: summary.pending_review_count || 0 },
    { label: '已阅卷', value: summary.graded_count || 0 },
    { label: '平均分', value: summary.average_score || 0 },
    { label: '最高分', value: summary.max_score || 0 },
    { label: '及格率', value: `${summary.pass_rate || 0}%` },
  ]
})

const filteredReportAttempts = computed(() => {
  const username = (reportQuery.value.username || '').trim().toLowerCase()
  const status = reportQuery.value.status
  const passed = reportQuery.value.passed

  return (activeReport.value?.attempts || []).filter((item) => {
    const itemUsername = (item.user?.username || '').toLowerCase()
    const matchUsername = !username || itemUsername.includes(username)
    const matchStatus = !status || item.status === status
    const matchPassed = passed === null || (item.status === 'graded' && item.is_passed === passed)
    return matchUsername && matchStatus && matchPassed
  })
})

function syncPassScoreWithinTotal(totalScore = questionTotalScore.value) {
  const currentPassScore = Number(modalForm.value.pass_score || 0)
  if (currentPassScore > totalScore) {
    modalForm.value.pass_score = totalScore
  }
}

watch(questionTotalScore, (totalScore) => syncPassScoreWithinTotal(totalScore), { immediate: true })

watch(
  () => modalForm.value.pass_score,
  () => syncPassScoreWithinTotal()
)

async function fetchBanks() {
  const { data } = await examApi.getExamBankList({ page: 1, page_size: 9999 })
  bankOptions.value = data.map((item) => ({
    label: item.name,
    value: item.id,
  }))
}

function rebuildQuestionSortOrder() {
  modalForm.value.questions = (modalForm.value.questions || []).map((item, index) => ({
    ...item,
    sort_order: index + 1,
  }))
}

function shuffleRows(rows) {
  const nextRows = [...rows]
  for (let index = nextRows.length - 1; index > 0; index -= 1) {
    const randomIndex = Math.floor(Math.random() * (index + 1))
    ;[nextRows[index], nextRows[randomIndex]] = [nextRows[randomIndex], nextRows[index]]
  }
  return nextRows
}

function formatPaperPayload(form) {
  const payload = {
    title: form.title,
    desc: form.desc || '',
    status: form.status,
    duration_minutes: Number(form.duration_minutes || 0),
    pass_score: Number(form.pass_score || 0),
    is_active: !!form.is_active,
    questions: (form.questions || []).map((item, index) => ({
      question_id: item.question_id,
      score: Number(item.score || 0),
      sort_order: index + 1,
    })),
  }
  if (form.id) {
    payload.id = form.id
  }
  return payload
}

function openAddPaper() {
  handleAdd()
  modalForm.value.questions = []
}

async function loadPaperDetail(paperId) {
  const { data } = await examApi.getExamPaperById({ paper_id: paperId })
  return {
    ...data,
    questions: (data.questions || []).map((item) => ({
      id: item.id,
      question_id: item.question_id,
      score: item.score,
      sort_order: item.sort_order,
      stem: item.question_snapshot?.stem || '',
      question_type: item.question_snapshot?.question_type || '',
      bank_id: item.question_snapshot?.bank_id || null,
      difficulty: item.question_snapshot?.difficulty || '',
      bank_name: item.question_snapshot?.bank_name || '',
    })),
  }
}

async function openEditPaper(row) {
  const data = await loadPaperDetail(row.id)
  handleEdit(data)
}

async function handleToggleActive(row) {
  row.publishing = true
  try {
    const detail = await loadPaperDetail(row.id)
    detail.is_active = !row.is_active
    await examApi.updateExamPaper(formatPaperPayload(detail))
    row.is_active = !row.is_active
    $message.success(row.is_active ? '已启用' : '已停用')
    $table.value?.handleSearch()
  } finally {
    row.publishing = false
  }
}

async function handlePublish(row) {
  await examApi.publishExamPaper({ paper_id: row.id })
  $message.success('试卷已发布')
  $table.value?.handleSearch()
}

async function handleClosePaper(row) {
  await examApi.closeExamPaper({ paper_id: row.id })
  $message.success('试卷已关闭')
  $table.value?.handleSearch()
}

function resetReportQuery() {
  reportQuery.value = {
    username: '',
    status: null,
    passed: null,
  }
}

async function loadPaperReport(paperId) {
  reportLoading.value = true
  try {
    const { data } = await examApi.getExamPaperAttempts({ paper_id: paperId })
    activeReport.value = data
  } finally {
    reportLoading.value = false
  }
}

async function openPaperReport(row) {
  activeReport.value = {
    paper: row,
    summary: {},
    attempts: [],
  }
  resetReportQuery()
  await loadPaperReport(row.id)
}

async function refreshPaperReport() {
  const paperId = activeReport.value?.paper?.id
  if (!paperId) return
  await loadPaperReport(paperId)
}

async function closePaperReport() {
  activeReport.value = null
  resetReportQuery()
  await nextTick()
  await $table.value?.handleSearch()
}

function moveQuestion(index, direction) {
  const questions = [...(modalForm.value.questions || [])]
  const nextIndex = direction === 'up' ? index - 1 : index + 1
  if (nextIndex < 0 || nextIndex >= questions.length) return
  ;[questions[index], questions[nextIndex]] = [questions[nextIndex], questions[index]]
  modalForm.value.questions = questions
  rebuildQuestionSortOrder()
}

function removeQuestion(index) {
  const questions = [...(modalForm.value.questions || [])]
  questions.splice(index, 1)
  modalForm.value.questions = questions
  rebuildQuestionSortOrder()
}

function shuffleCurrentQuestions() {
  const questions = modalForm.value.questions || []
  if (questions.length < 2) {
    $message.warning('至少选择 2 道题后才能打乱题序')
    return
  }

  let nextQuestions = shuffleRows(questions)
  const isSameOrder = questions.every(
    (item, index) => item.question_id === nextQuestions[index]?.question_id
  )
  if (isSameOrder) {
    nextQuestions = [...nextQuestions.slice(1), nextQuestions[0]]
  }

  modalForm.value.questions = nextQuestions
  rebuildQuestionSortOrder()
  $message.success('已打乱当前题序')
}

function normalizeSelectorQuestionRow(item) {
  if (!item) return null

  const id = Number(item.id || item.question_id || 0)
  if (!id) return null

  return {
    id,
    default_score: Number(item.default_score ?? item.score ?? 0),
    stem: item.stem || '',
    question_type: item.question_type || '',
    bank_id: item.bank_id ?? null,
    bank_name: item.bank_name || '',
    difficulty: item.difficulty || '',
  }
}

function syncSelectorCheckedRows(keys = selectorCheckedRowKeys.value, rows = []) {
  const rowMap = new Map()
  ;[
    ...(selectorCheckedRows.value || []),
    ...(rows || []),
    ...(selectorRows.value || []),
    ...(modalForm.value.questions || []),
  ]
    .map((item) => normalizeSelectorQuestionRow(item))
    .filter(Boolean)
    .forEach((item) => {
      rowMap.set(item.id, item)
    })

  selectorCheckedRows.value = (keys || []).map((key) => rowMap.get(Number(key))).filter(Boolean)
}

async function loadSelectorRows() {
  selectorLoading.value = true
  try {
    const { data } = await examApi.getExamQuestionList({
      page: 1,
      page_size: 9999,
      selectable_only: true,
      ...selectorQuery.value,
    })
    selectorRows.value = data
    syncSelectorCheckedRows()
  } finally {
    selectorLoading.value = false
  }
}

async function openQuestionSelector() {
  selectorVisible.value = true
  selectorCheckedRowKeys.value = (modalForm.value.questions || []).map((item) => item.question_id)
  await loadSelectorRows()
}

function handleSelectorChecked(keys, rows) {
  selectorCheckedRowKeys.value = keys
  syncSelectorCheckedRows(keys, rows)
}

function handleRandomSelectQuestions() {
  const count = Number(selectorRandomCount.value || 0)
  if (count < 1) {
    $message.warning('请输入随机选择题目数量')
    return
  }

  const selectedIds = new Set((selectorCheckedRowKeys.value || []).map((item) => Number(item)))
  const candidates = (selectorRows.value || [])
    .map((item) => normalizeSelectorQuestionRow(item))
    .filter((item) => item && !selectedIds.has(item.id))

  if (!candidates.length) {
    $message.warning('当前条件下没有可随机选择的题目')
    return
  }

  const pickedRows = shuffleRows(candidates).slice(0, count)
  const nextKeys = [...selectedIds, ...pickedRows.map((item) => item.id)]

  selectorCheckedRowKeys.value = nextKeys
  syncSelectorCheckedRows(nextKeys, pickedRows)

  if (pickedRows.length < count) {
    $message.warning(`当前条件下仅剩 ${pickedRows.length} 道可选题，已全部选中`)
    return
  }
  $message.success(`已随机选择 ${pickedRows.length} 道题`)
}

function handleConfirmSelectQuestions() {
  const existingIds = new Set((modalForm.value.questions || []).map((item) => item.question_id))
  const nextQuestions = [...(modalForm.value.questions || [])]

  selectorCheckedRows.value.forEach((item) => {
    if (existingIds.has(item.id)) return
    nextQuestions.push({
      question_id: item.id,
      score: item.default_score,
      sort_order: nextQuestions.length + 1,
      stem: item.stem,
      question_type: item.question_type,
      bank_id: item.bank_id,
      bank_name: item.bank_name,
      difficulty: item.difficulty,
    })
  })

  modalForm.value.questions = nextQuestions
  rebuildQuestionSortOrder()
  selectorVisible.value = false
}

const selectorColumns = [
  {
    type: 'selection',
  },
  {
    title: '题干',
    key: 'stem',
    ellipsis: { tooltip: true },
  },
  {
    title: '题库',
    key: 'bank_name',
    width: 120,
  },
  {
    title: '题型',
    key: 'question_type',
    width: 100,
    render(row) {
      return QUESTION_TYPE_LABEL_MAP[row.question_type] || row.question_type
    },
  },
  {
    title: '难度',
    key: 'difficulty',
    width: 80,
    render(row) {
      return DIFFICULTY_LABEL_MAP[row.difficulty] || row.difficulty
    },
  },
  {
    title: '分值',
    key: 'default_score',
    width: 80,
  },
]

function renderStatus(status) {
  const type = status === 'published' ? 'success' : status === 'closed' ? 'error' : 'warning'
  return h(NTag, { type }, { default: () => PAPER_STATUS_LABEL_MAP[status] || status })
}

function renderAttemptStatus(status) {
  const type = status === 'graded' ? 'success' : status === 'pending_review' ? 'warning' : 'info'
  return h(
    NTag,
    { type, bordered: false },
    { default: () => ATTEMPT_STATUS_LABEL_MAP[status] || status }
  )
}

function renderPassStatus(row) {
  if (row.status !== 'graded') {
    return h(NTag, { bordered: false }, { default: () => '未出分' })
  }
  return h(
    NTag,
    { type: row.is_passed ? 'success' : 'error', bordered: false },
    { default: () => (row.is_passed ? '及格' : '未及格') }
  )
}

const reportColumns = [
  {
    title: '答题人',
    key: 'user.username',
    width: 120,
    align: 'center',
    render(row) {
      return row.user?.username || '-'
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 120,
    align: 'center',
    render(row) {
      return renderAttemptStatus(row.status)
    },
  },
  {
    title: '客观题得分',
    key: 'objective_score',
    width: 110,
    align: 'center',
  },
  {
    title: '主观题得分',
    key: 'subjective_score',
    width: 110,
    align: 'center',
  },
  {
    title: '总分',
    key: 'total_score',
    width: 90,
    align: 'center',
  },
  {
    title: '结果',
    key: 'is_passed',
    width: 100,
    align: 'center',
    render(row) {
      return renderPassStatus(row)
    },
  },
  {
    title: '提交时间',
    key: 'submitted_at',
    width: 160,
    align: 'center',
    render(row) {
      return row.submitted_at ? formatDate(row.submitted_at, 'YYYY-MM-DD HH:mm:ss') : '-'
    },
  },
  {
    title: '阅卷人',
    key: 'graded_by_user.username',
    width: 120,
    align: 'center',
    render(row) {
      return row.graded_by_user?.username || row.claimed_by_name || '-'
    },
  },
]

const columns = [
  {
    title: '试卷标题',
    key: 'title',
    align: 'center',
    width: 180,
    ellipsis: { tooltip: true },
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
    title: '题目数',
    key: 'question_count',
    align: 'center',
    width: 70,
  },
  {
    title: '总分',
    key: 'total_score',
    align: 'center',
    width: 70,
  },
  {
    title: '及格分',
    key: 'pass_score',
    align: 'center',
    width: 70,
  },
  {
    title: '限时(分钟)',
    key: 'duration_minutes',
    align: 'center',
    width: 90,
  },
  {
    title: '已有答卷',
    key: 'has_attempts',
    align: 'center',
    width: 80,
    render(row) {
      return h(
        NTag,
        { type: row.has_attempts ? 'warning' : 'default' },
        { default: () => (row.has_attempts ? '是' : '否') }
      )
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
    width: 360,
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
              onClick: () => openEditPaper(row),
            },
            {
              default: () => '编辑',
              icon: renderIcon('material-symbols:edit-outline', { size: 16 }),
            }
          ),
          [[vPermission, 'post/api/v1/exam/paper/update']]
        ),
        row.status !== 'published'
          ? withDirectives(
              h(
                NButton,
                {
                  size: 'small',
                  quaternary: true,
                  type: 'success',
                  onClick: () => handlePublish(row),
                },
                {
                  default: () => '发布',
                }
              ),
              [[vPermission, 'post/api/v1/exam/paper/publish']]
            )
          : withDirectives(
              h(
                NButton,
                {
                  size: 'small',
                  quaternary: true,
                  type: 'warning',
                  onClick: () => handleClosePaper(row),
                },
                {
                  default: () => '关闭',
                }
              ),
              [[vPermission, 'post/api/v1/exam/paper/close']]
            ),
        withDirectives(
          h(
            NButton,
            {
              size: 'small',
              quaternary: true,
              type: 'info',
              onClick: () => openPaperReport(row),
            },
            {
              default: () => '作答情况',
              icon: renderIcon('material-symbols:analytics-outline-rounded', { size: 16 }),
            }
          ),
          [[vPermission, 'get/api/v1/exam/paper/attempts']]
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => handleDelete({ paper_id: row.id }),
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
                [[vPermission, 'delete/api/v1/exam/paper/delete']]
              ),
            default: () => h('div', {}, '确定删除该试卷吗?'),
          }
        ),
      ]
    },
  },
]
</script>

<template>
  <CommonPage show-footer :title="activeReport ? '作答情况' : '试卷管理'">
    <template #action>
      <div v-if="activeReport" class="exam-paper-report-actions">
        <NButton @click="closePaperReport">返回列表</NButton>
        <NButton type="primary" :loading="reportLoading" @click="refreshPaperReport">刷新</NButton>
      </div>
      <NButton
        v-else
        v-permission="'post/api/v1/exam/paper/create'"
        type="primary"
        @click="openAddPaper"
      >
        <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />新建试卷
      </NButton>
    </template>

    <NSpin v-if="activeReport" :show="reportLoading">
      <section class="exam-paper-report" :class="{ 'is-dark': appStore.isDark }">
        <header class="exam-paper-report-header">
          <div>
            <h2>{{ activeReport.paper?.title || '作答情况' }}</h2>
            <p>
              总分：{{ activeReport.paper?.total_score || 0 }}，及格分：{{
                activeReport.paper?.pass_score || 0
              }}，题目数：{{ activeReport.paper?.question_count || 0 }}
            </p>
          </div>
          <NTag :type="activeReport.paper?.is_active ? 'success' : 'default'" :bordered="false">
            {{ activeReport.paper?.is_active ? '启用' : '停用' }}
          </NTag>
        </header>

        <div class="exam-paper-report-stats">
          <section v-for="item in reportSummaryItems" :key="item.label" class="exam-paper-stat">
            <span>{{ item.label }}</span>
            <strong>{{ item.value }}</strong>
          </section>
        </div>

        <div class="exam-paper-report-query">
          <NInput
            v-model:value="reportQuery.username"
            clearable
            placeholder="答题人"
            class="exam-paper-report-search"
          />
          <NSelect
            v-model:value="reportQuery.status"
            clearable
            :options="attemptStatusOptions"
            placeholder="答卷状态"
            class="exam-paper-report-select"
          />
          <NSelect
            v-model:value="reportQuery.passed"
            clearable
            :options="passFilterOptions"
            placeholder="及格情况"
            class="exam-paper-report-select"
          />
          <NButton @click="resetReportQuery">重置</NButton>
        </div>

        <NDataTable
          :columns="reportColumns"
          :data="filteredReportAttempts"
          :pagination="false"
          :row-key="(row) => row.id"
          :scroll-x="980"
        />
      </section>
    </NSpin>

    <CrudTable
      v-else
      ref="$table"
      v-model:query-items="queryItems"
      :columns="columns"
      :get-data="examApi.getExamPaperList"
      :scroll-x="1600"
    >
      <template #queryBar>
        <QueryBarItem label="试卷标题">
          <NInput
            v-model:value="queryItems.title"
            clearable
            placeholder="请输入试卷标题"
            @keypress.enter="$table?.handleSearch()"
          />
        </QueryBarItem>
        <QueryBarItem label="试卷状态">
          <NSelect
            v-model:value="queryItems.status"
            clearable
            :options="paperStatusOptions"
            placeholder="请选择试卷状态"
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
      style="width: 1120px"
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
        <NFormItem label="试卷标题" path="title">
          <NInput v-model:value="modalForm.title" placeholder="请输入试卷标题" />
        </NFormItem>
        <NFormItem label="试卷说明" path="desc">
          <NInput
            v-model:value="modalForm.desc"
            type="textarea"
            placeholder="请输入试卷说明"
            :autosize="{ minRows: 3, maxRows: 5 }"
          />
        </NFormItem>
        <div class="exam-paper-grid">
          <NFormItem label="状态" path="status">
            <NSelect
              v-model:value="modalForm.status"
              :options="paperStatusOptions"
              placeholder="请选择状态"
            />
          </NFormItem>
          <NFormItem label="启用状态" path="is_active">
            <NSwitch v-model:value="modalForm.is_active" />
          </NFormItem>
          <NFormItem label="限时分钟" path="duration_minutes">
            <NInputNumber v-model:value="modalForm.duration_minutes" :min="0" />
          </NFormItem>
          <NFormItem label="及格分" path="pass_score">
            <NInputNumber
              v-model:value="modalForm.pass_score"
              :min="0"
              :max="questionTotalScore"
              :precision="2"
            />
          </NFormItem>
        </div>

        <NFormItem label="试卷题目">
          <div class="exam-paper-question-wrap">
            <div class="exam-paper-toolbar">
              <div class="exam-paper-toolbar-actions">
                <NButton type="primary" @click="openQuestionSelector">
                  <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />添加题目
                </NButton>
                <NButton
                  secondary
                  type="primary"
                  :disabled="(modalForm.questions?.length || 0) < 2"
                  @click="shuffleCurrentQuestions"
                >
                  <TheIcon icon="material-symbols:shuffle" :size="18" class="mr-5" />打乱题序
                </NButton>
              </div>
              <span>
                当前已选择 {{ modalForm.questions?.length || 0 }} 道题目，合计
                {{ questionTotalScore }} 分
              </span>
            </div>
            <div v-if="modalForm.questions?.length" class="exam-paper-question-list">
              <section
                v-for="(item, index) in modalForm.questions"
                :key="`${item.question_id}-${index}`"
                class="exam-paper-question-card"
              >
                <header>
                  <div>
                    <strong>第 {{ index + 1 }} 题</strong>
                    <NTag size="small" type="info" :bordered="false">
                      {{ QUESTION_TYPE_LABEL_MAP[item.question_type] || item.question_type }}
                    </NTag>
                  </div>
                  <div class="exam-paper-question-actions">
                    <NButton
                      text
                      type="primary"
                      :disabled="index === 0"
                      @click="moveQuestion(index, 'up')"
                      >上移</NButton
                    >
                    <NButton
                      text
                      type="primary"
                      :disabled="index === modalForm.questions.length - 1"
                      @click="moveQuestion(index, 'down')"
                    >
                      下移
                    </NButton>
                    <NButton text type="error" @click="removeQuestion(index)">移除</NButton>
                  </div>
                </header>
                <p>{{ item.stem }}</p>
                <div class="exam-paper-question-meta">
                  <span>题库：{{ item.bank_name || '-' }}</span>
                  <span
                    >难度：{{
                      DIFFICULTY_LABEL_MAP[item.difficulty] || item.difficulty || '-'
                    }}</span
                  >
                </div>
                <div class="exam-paper-score">
                  <span>本题分值</span>
                  <NInputNumber v-model:value="item.score" :min="1" :precision="2" />
                </div>
              </section>
            </div>
            <div v-else class="exam-paper-empty">请先选择试卷题目</div>
          </div>
        </NFormItem>
      </NForm>
    </CrudModal>

    <NModal
      v-model:show="selectorVisible"
      preset="card"
      title="选择题目"
      style="width: 1180px"
      :mask-closable="false"
    >
      <div class="exam-paper-selector-query">
        <NSelect
          v-model:value="selectorQuery.bank_id"
          clearable
          :options="bankOptions"
          placeholder="题库"
        />
        <NSelect
          v-model:value="selectorQuery.question_type"
          clearable
          :options="questionTypeOptions"
          placeholder="题型"
        />
        <NSelect
          v-model:value="selectorQuery.difficulty"
          clearable
          :options="difficultyOptions"
          placeholder="难度"
        />
        <NInput
          v-model:value="selectorQuery.stem"
          clearable
          placeholder="请输入题干关键字"
          @keypress.enter="loadSelectorRows"
        />
        <NButton type="primary" @click="loadSelectorRows">搜索</NButton>
      </div>

      <div class="exam-paper-selector-tools">
        <div class="exam-paper-random-picker">
          <span>随机选择</span>
          <NInputNumber
            v-model:value="selectorRandomCount"
            :min="1"
            :precision="0"
            placeholder="题数"
            style="width: 120px"
          />
          <NButton
            secondary
            type="primary"
            :disabled="selectorRandomAvailableCount < 1"
            @click="handleRandomSelectQuestions"
          >
            <TheIcon icon="material-symbols:casino-outline" :size="18" class="mr-5" />随机勾选
          </NButton>
        </div>
        <span>已选 {{ selectorCheckedRowKeys.length }} 道</span>
      </div>

      <NDataTable
        remote
        :loading="selectorLoading"
        :columns="selectorColumns"
        :data="selectorRows"
        :row-key="(row) => row.id"
        :checked-row-keys="selectorCheckedRowKeys"
        :scroll-x="1050"
        @update:checked-row-keys="handleSelectorChecked"
      />

      <template #footer>
        <div class="flex justify-end gap-12">
          <NButton @click="selectorVisible = false">取消</NButton>
          <NButton type="primary" @click="handleConfirmSelectQuestions">加入试卷</NButton>
        </div>
      </template>
    </NModal>
  </CommonPage>
</template>

<style scoped lang="scss">
.exam-paper-report-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.exam-paper-report {
  --exam-paper-report-bg: #fff;
  --exam-paper-report-fill: #f8fafc;
  --exam-paper-report-border: #e5e7eb;
  --exam-paper-report-text: #111827;
  --exam-paper-report-muted: #64748b;
  --exam-paper-report-accent: var(--primary-color);

  display: flex;
  flex-direction: column;
  gap: 18px;
  color: var(--exam-paper-report-text);
}

.exam-paper-report.is-dark {
  --exam-paper-report-bg: #000;
  --exam-paper-report-fill: #18191d;
  --exam-paper-report-border: #2a2b30;
  --exam-paper-report-text: rgba(255, 255, 255, 0.88);
  --exam-paper-report-muted: rgba(255, 255, 255, 0.62);
}

.exam-paper-report-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 18px 20px;
  border: 1px solid var(--exam-paper-report-border);
  border-radius: 8px;
  background: var(--exam-paper-report-bg);

  h2 {
    margin: 0;
    font-size: 22px;
    font-weight: 600;
    color: var(--exam-paper-report-text);
  }

  p {
    margin: 8px 0 0;
    color: var(--exam-paper-report-muted);
    line-height: 1.7;
  }
}

.exam-paper-report-stats {
  display: grid;
  grid-template-columns: repeat(7, minmax(0, 1fr));
  gap: 12px;
}

.exam-paper-stat {
  min-height: 90px;
  padding: 14px 16px;
  border: 1px solid var(--exam-paper-report-border);
  border-radius: 8px;
  background: var(--exam-paper-report-fill);

  span {
    display: block;
    margin-bottom: 10px;
    color: var(--exam-paper-report-muted);
    font-size: 13px;
  }

  strong {
    color: var(--exam-paper-report-text);
    font-size: 24px;
    font-weight: 650;
  }
}

.exam-paper-report-query {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 14px 16px;
  border: 1px solid var(--exam-paper-report-border);
  border-radius: 8px;
  background: var(--exam-paper-report-bg);
  flex-wrap: wrap;
}

.exam-paper-report-search {
  width: 220px;
}

.exam-paper-report-select {
  width: 160px;
}

.exam-paper-grid {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 0 16px;
}

.exam-paper-question-wrap {
  width: 100%;
}

.exam-paper-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin-bottom: 14px;
  gap: 12px;
  flex-wrap: wrap;
}

.exam-paper-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.exam-paper-question-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.exam-paper-question-card {
  padding: 14px 16px;
  border: 1px solid #e5e7eb;
  border-radius: 14px;
  background: #fafaf9;

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }

  p {
    margin: 0 0 10px;
    line-height: 1.7;
    color: #1f2937;
  }
}

.exam-paper-question-actions {
  display: flex;
  gap: 4px;
  flex-wrap: wrap;
}

.exam-paper-question-meta {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  color: #64748b;
  font-size: 13px;
}

.exam-paper-score {
  display: flex;
  align-items: center;
  gap: 12px;
  margin-top: 10px;
}

.exam-paper-empty {
  padding: 28px 16px;
  border: 1px dashed #cbd5e1;
  border-radius: 14px;
  color: #64748b;
  text-align: center;
}

.exam-paper-selector-query {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.exam-paper-selector-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  color: #64748b;
  flex-wrap: wrap;
}

.exam-paper-random-picker {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 960px) {
  .exam-paper-report-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .exam-paper-report-search,
  .exam-paper-report-select {
    width: 100%;
  }

  .exam-paper-grid,
  .exam-paper-selector-query {
    grid-template-columns: 1fr;
  }

  .exam-paper-question-card header {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
