<script setup>
import { computed, h, nextTick, onMounted, ref } from 'vue'
import {
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NDataTable,
  NEmpty,
  NInput,
  NInputNumber,
  NLayout,
  NLayoutContent,
  NLayoutSider,
  NModal,
  NPopconfirm,
  NRadio,
  NRadioGroup,
  NSelect,
  NSpin,
  NTag,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import TheIcon from '@/components/icon/TheIcon.vue'
import examApi from '@/api/exam'
import { useAppStore } from '@/store'
import { formatDate } from '@/utils'

import {
  DIFFICULTY_LABEL_MAP,
  PRACTICE_STATUS_LABEL_MAP,
  QUESTION_TYPE_LABEL_MAP,
  difficultyOptions,
  questionTypeOptions,
} from '../constants'

defineOptions({ name: '练习中心' })

const appStore = useAppStore()
const loading = ref(false)
const sessionLoading = ref(false)
const historyRows = ref([])
const activeSession = ref(null)
const activeAnswerIndex = ref(0)
const bankOptions = ref([])
const answerDrafts = ref({})
const selectedQuestions = ref([])
const selectorVisible = ref(false)
const selectorLoading = ref(false)
const selectorRows = ref([])
const selectorCheckedRowKeys = ref([])
const selectorCheckedRows = ref([])
const selectorRandomCount = ref(1)
const selectorQuery = ref({
  bank_id: null,
  question_type: null,
  difficulty: null,
  stem: '',
})

const activeAnswer = computed(() => {
  return activeSession.value?.answers?.[activeAnswerIndex.value] || null
})

const answeredRate = computed(() => {
  const session = activeSession.value
  if (!session?.question_count) return 0
  return Math.round(
    (Number(session.answered_count || 0) / Number(session.question_count || 1)) * 100
  )
})

const selectorRandomAvailableCount = computed(() => {
  const selectedIds = new Set((selectorCheckedRowKeys.value || []).map((item) => Number(item)))
  return (selectorRows.value || []).filter((item) => !selectedIds.has(Number(item.id))).length
})

onMounted(async () => {
  await Promise.all([loadBanks(), loadPracticeHistory()])
})

async function loadBanks() {
  const { data } = await examApi.getExamPracticeBankList()
  bankOptions.value = data.map((item) => ({
    label: item.name,
    value: item.id,
  }))
}

function getInitialDraft(answer) {
  if (!answer) return null
  if (answer.question_type === 'multiple_choice') return answer.answer_payload || []
  if (answer.question_type === 'single_choice' || answer.question_type === 'true_false') {
    return Array.isArray(answer.answer_payload) ? answer.answer_payload[0] || null : null
  }
  return answer.answer_payload || ''
}

function normalizeSession(data) {
  const session = {
    ...data,
    answers: data.answers || [],
  }
  const drafts = {}
  session.answers.forEach((answer) => {
    drafts[answer.id] = getInitialDraft(answer)
  })
  answerDrafts.value = drafts
  return session
}

async function loadPracticeHistory() {
  loading.value = true
  try {
    const { data } = await examApi.getMyExamPracticeList({ page: 1, page_size: 20 })
    historyRows.value = data
  } finally {
    loading.value = false
  }
}

async function startPractice() {
  if (!selectedQuestions.value.length) {
    $message.warning('请先选择练习题目')
    return
  }

  const bankIds = [...new Set(selectedQuestions.value.map((item) => item.bank_id).filter(Boolean))]
  const questionTypes = [
    ...new Set(selectedQuestions.value.map((item) => item.question_type).filter(Boolean)),
  ]
  const difficulties = [
    ...new Set(selectedQuestions.value.map((item) => item.difficulty).filter(Boolean)),
  ]

  sessionLoading.value = true
  try {
    const { data } = await examApi.startExamPractice({
      bank_id: bankIds.length === 1 ? bankIds[0] : null,
      question_type: questionTypes.length === 1 ? questionTypes[0] : null,
      difficulty: difficulties.length === 1 ? difficulties[0] : null,
      question_count: selectedQuestions.value.length,
      question_ids: selectedQuestions.value.map((item) => item.id),
    })
    activeSession.value = normalizeSession(data)
    activeAnswerIndex.value = 0
    await loadPracticeHistory()
  } finally {
    sessionLoading.value = false
  }
}

async function openPracticeSession(row) {
  sessionLoading.value = true
  try {
    const { data } = await examApi.getExamPracticeById({ session_id: row.id })
    activeSession.value = normalizeSession(data)
    activeAnswerIndex.value = 0
  } finally {
    sessionLoading.value = false
  }
}

async function submitCurrentAnswer() {
  if (!activeAnswer.value) return
  sessionLoading.value = true
  try {
    const { data } = await examApi.answerExamPractice({
      answer_id: activeAnswer.value.id,
      answer_payload: answerDrafts.value[activeAnswer.value.id],
    })
    activeSession.value = normalizeSession(data)
    await loadPracticeHistory()
  } finally {
    sessionLoading.value = false
  }
}

async function finishPractice() {
  if (!activeSession.value?.id) return
  sessionLoading.value = true
  try {
    const { data } = await examApi.finishExamPractice({ session_id: activeSession.value.id })
    activeSession.value = normalizeSession(data)
    await loadPracticeHistory()
  } finally {
    sessionLoading.value = false
  }
}

async function closePractice() {
  activeSession.value = null
  activeAnswerIndex.value = 0
  answerDrafts.value = {}
  await nextTick()
  await loadPracticeHistory()
}

async function retryPractice(row) {
  if (!row?.id) return
  sessionLoading.value = true
  try {
    const { data } = await examApi.retryExamPractice({ session_id: row.id })
    activeSession.value = normalizeSession(data)
    activeAnswerIndex.value = 0
    await loadPracticeHistory()
    $message.success('已生成新的练习')
  } finally {
    sessionLoading.value = false
  }
}

async function deletePractice(row) {
  if (!row?.id) return
  loading.value = true
  try {
    await examApi.deleteExamPractice({ session_id: row.id })
    await loadPracticeHistory()
    $message.success('已删除练习记录')
  } finally {
    loading.value = false
  }
}

function goNextAnswer() {
  const nextIndex = activeAnswerIndex.value + 1
  if (nextIndex < (activeSession.value?.answers || []).length) {
    activeAnswerIndex.value = nextIndex
  }
}

function shuffleRows(rows) {
  return [...rows].sort(() => Math.random() - 0.5)
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
    ...selectedQuestions.value,
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
    const { data } = await examApi.getExamPracticeQuestionList({
      page: 1,
      page_size: 9999,
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
  selectorCheckedRowKeys.value = selectedQuestions.value.map((item) => item.id)
  selectorCheckedRows.value = [...selectedQuestions.value]
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
  selectedQuestions.value = selectorCheckedRows.value
    .map((item) => normalizeSelectorQuestionRow(item))
    .filter(Boolean)
  selectorVisible.value = false
}

function removeSelectedQuestion(index) {
  selectedQuestions.value.splice(index, 1)
}

function findOptionLabel(snapshot, value) {
  if (value === 'TRUE') return '正确'
  if (value === 'FALSE') return '错误'
  const option = (snapshot.options || []).find((item) => item.option_key === value)
  return option ? `${option.option_key}. ${option.option_content}` : value
}

function renderAnswerValue(answer) {
  if (!answer) return '-'
  if (answer.question_type === 'multiple_choice') {
    return Array.isArray(answer.answer_payload) && answer.answer_payload.length
      ? answer.answer_payload
          .map((item) => findOptionLabel(answer.answer_snapshot, item))
          .join('、')
      : '未作答'
  }
  if (answer.question_type === 'single_choice' || answer.question_type === 'true_false') {
    const values = Array.isArray(answer.answer_payload) ? answer.answer_payload : []
    return values.length ? findOptionLabel(answer.answer_snapshot, values[0]) : '未作答'
  }
  return answer.answer_payload || '未作答'
}

function renderCorrectAnswer(answer) {
  if (!answer?.reveal_answer) return '-'
  const snapshot = answer.answer_snapshot || {}
  const correctAnswer = snapshot.correct_answer || []
  if (answer.question_type === 'multiple_choice') {
    return correctAnswer.map((item) => findOptionLabel(snapshot, item)).join('、') || '-'
  }
  if (answer.question_type === 'single_choice' || answer.question_type === 'true_false') {
    return correctAnswer.length ? findOptionLabel(snapshot, correctAnswer[0]) : '-'
  }
  return snapshot.reference_answer || '-'
}

function renderPracticeStatus(status) {
  const type = status === 'completed' ? 'success' : 'warning'
  return h(
    NTag,
    { type, bordered: false },
    { default: () => PRACTICE_STATUS_LABEL_MAP[status] || status }
  )
}

function renderCorrectRate(row) {
  const total = Number(row.answered_count || 0)
  if (!total) return '0%'
  return `${Math.round((Number(row.correct_count || 0) / total) * 100)}%`
}

const historyColumns = [
  {
    title: '状态',
    key: 'status',
    width: 100,
    align: 'center',
    render(row) {
      return renderPracticeStatus(row.status)
    },
  },
  {
    title: '题库',
    key: 'bank.name',
    ellipsis: { tooltip: true },
    render(row) {
      return row.bank?.name || '综合练习'
    },
  },
  {
    title: '题型',
    key: 'question_type',
    width: 100,
    align: 'center',
    render(row) {
      return row.question_type
        ? QUESTION_TYPE_LABEL_MAP[row.question_type] || row.question_type
        : '不限'
    },
  },
  {
    title: '难度',
    key: 'difficulty',
    width: 90,
    align: 'center',
    render(row) {
      return row.difficulty ? DIFFICULTY_LABEL_MAP[row.difficulty] || row.difficulty : '不限'
    },
  },
  {
    title: '进度',
    key: 'answered_count',
    width: 100,
    align: 'center',
    render(row) {
      return `${row.answered_count || 0}/${row.question_count || 0}`
    },
  },
  {
    title: '正确率',
    key: 'correct_count',
    width: 90,
    align: 'center',
    render(row) {
      return renderCorrectRate(row)
    },
  },
  {
    title: '开始时间',
    key: 'started_at',
    width: 160,
    align: 'center',
    render(row) {
      return row.started_at ? formatDate(row.started_at, 'YYYY-MM-DD HH:mm:ss') : '-'
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 220,
    align: 'center',
    render(row) {
      return h('div', { class: 'exam-practice-history-actions' }, [
        h(
          NButton,
          {
            size: 'small',
            type: 'primary',
            onClick: () => openPracticeSession(row),
          },
          { default: () => (row.status === 'completed' ? '查看' : '继续') }
        ),
        h(
          NButton,
          {
            size: 'small',
            secondary: true,
            type: 'primary',
            onClick: () => retryPractice(row),
          },
          { default: () => '重新练习' }
        ),
        h(
          NPopconfirm,
          {
            onPositiveClick: () => deletePractice(row),
          },
          {
            trigger: () =>
              h(
                NButton,
                {
                  size: 'small',
                  secondary: true,
                  type: 'error',
                },
                { default: () => '删除' }
              ),
            default: () => '确认删除这条练习记录？',
          }
        ),
      ])
    },
  },
]

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
</script>

<template>
  <CommonPage show-footer :title="activeSession ? '练习作答' : '练习中心'">
    <template #action>
      <div v-if="activeSession" class="exam-practice-header-actions">
        <NButton @click="closePractice">返回练习中心</NButton>
        <NButton
          v-if="activeSession.status === 'in_progress'"
          type="primary"
          secondary
          @click="finishPractice"
        >
          完成练习
        </NButton>
      </div>
    </template>

    <NSpin :show="loading || sessionLoading">
      <div v-if="!activeSession" class="exam-practice-home" :class="{ 'is-dark': appStore.isDark }">
        <section class="exam-practice-start">
          <div class="exam-practice-start-header">
            <div>
              <h2>生成练习</h2>
              <p>从题库中多选题目，生成一组可即时查看答案的练习。</p>
            </div>
            <NButton type="primary" :disabled="!selectedQuestions.length" @click="startPractice">
              开始练习
            </NButton>
          </div>

          <div class="exam-practice-question-wrap">
            <div class="exam-practice-toolbar">
              <div class="exam-practice-toolbar-actions">
                <NButton type="primary" @click="openQuestionSelector">
                  <TheIcon icon="material-symbols:add" :size="18" class="mr-5" />添加题目
                </NButton>
              </div>
              <span>当前已选择 {{ selectedQuestions.length }} 道题目</span>
            </div>
            <div v-if="selectedQuestions.length" class="exam-practice-question-list">
              <section
                v-for="(item, index) in selectedQuestions"
                :key="`${item.id}-${index}`"
                class="exam-practice-question-card"
              >
                <header>
                  <div>
                    <strong>第 {{ index + 1 }} 题</strong>
                    <NTag size="small" type="info" :bordered="false">
                      {{ QUESTION_TYPE_LABEL_MAP[item.question_type] || item.question_type }}
                    </NTag>
                  </div>
                  <NButton text type="error" @click="removeSelectedQuestion(index)">移除</NButton>
                </header>
                <p>{{ item.stem }}</p>
                <div class="exam-practice-question-meta">
                  <span>题库：{{ item.bank_name || '-' }}</span>
                  <span
                    >难度：{{
                      DIFFICULTY_LABEL_MAP[item.difficulty] || item.difficulty || '-'
                    }}</span
                  >
                  <span>分值：{{ item.default_score || 0 }}</span>
                </div>
              </section>
            </div>
            <div v-else class="exam-practice-empty">请先选择练习题目</div>
          </div>
        </section>

        <section class="exam-practice-history">
          <header>
            <h3>练习记录</h3>
            <NButton secondary type="primary" @click="loadPracticeHistory">刷新</NButton>
          </header>
          <NEmpty v-if="!historyRows.length" description="暂无练习记录" />
          <NDataTable
            v-else
            :columns="historyColumns"
            :data="historyRows"
            :pagination="false"
            :row-key="(row) => row.id"
            :scroll-x="980"
          />
        </section>
      </div>

      <NLayout
        v-else
        has-sider
        class="exam-practice-layout"
        :class="{ 'is-dark': appStore.isDark }"
      >
        <NLayoutSider
          bordered
          content-style="padding: 18px 10px 18px 14px; height: 100%;"
          :width="230"
          class="exam-practice-sider"
        >
          <div class="exam-practice-summary">
            <p>进度：{{ activeSession.answered_count }}/{{ activeSession.question_count }}</p>
            <p>正确：{{ activeSession.correct_count }}</p>
            <p>错误：{{ activeSession.wrong_count }}</p>
            <p>完成度：{{ answeredRate }}%</p>
          </div>

          <div class="exam-practice-nav">
            <button
              v-for="(item, index) in activeSession.answers"
              :key="item.id"
              type="button"
              :class="[
                'exam-practice-nav-item',
                {
                  active: index === activeAnswerIndex,
                  answered: item.answered_at,
                  correct: item.is_correct === true,
                  wrong: item.is_correct === false,
                },
              ]"
              @click="activeAnswerIndex = index"
            >
              <span>第 {{ index + 1 }} 题</span>
              <small>{{ QUESTION_TYPE_LABEL_MAP[item.question_type] || item.question_type }}</small>
            </button>
          </div>
        </NLayoutSider>

        <NLayoutContent class="exam-practice-content">
          <section v-if="activeAnswer" class="exam-practice-card">
            <header class="exam-practice-card-header">
              <div>
                <h3>第 {{ activeAnswerIndex + 1 }} 题</h3>
                <NTag type="info" :bordered="false">
                  {{
                    QUESTION_TYPE_LABEL_MAP[activeAnswer.question_type] ||
                    activeAnswer.question_type
                  }}
                </NTag>
              </div>
              <NTag
                v-if="activeAnswer.reveal_answer"
                :type="
                  activeAnswer.is_correct
                    ? 'success'
                    : activeAnswer.is_correct === false
                    ? 'error'
                    : 'warning'
                "
                :bordered="false"
              >
                {{
                  activeAnswer.is_correct === true
                    ? '回答正确'
                    : activeAnswer.is_correct === false
                    ? '回答错误'
                    : '已查看答案'
                }}
              </NTag>
            </header>

            <p class="exam-practice-stem">{{ activeAnswer.answer_snapshot?.stem }}</p>

            <div class="exam-practice-answer">
              <NRadioGroup
                v-if="activeAnswer.question_type === 'single_choice'"
                v-model:value="answerDrafts[activeAnswer.id]"
                :disabled="!!activeAnswer.answered_at || activeSession.status !== 'in_progress'"
              >
                <NRadio
                  v-for="option in activeAnswer.answer_snapshot?.options || []"
                  :key="option.option_key"
                  :value="option.option_key"
                >
                  {{ option.option_key }}. {{ option.option_content }}
                </NRadio>
              </NRadioGroup>

              <NCheckboxGroup
                v-else-if="activeAnswer.question_type === 'multiple_choice'"
                v-model:value="answerDrafts[activeAnswer.id]"
                :disabled="!!activeAnswer.answered_at || activeSession.status !== 'in_progress'"
              >
                <NCheckbox
                  v-for="option in activeAnswer.answer_snapshot?.options || []"
                  :key="option.option_key"
                  :value="option.option_key"
                >
                  {{ option.option_key }}. {{ option.option_content }}
                </NCheckbox>
              </NCheckboxGroup>

              <NRadioGroup
                v-else-if="activeAnswer.question_type === 'true_false'"
                v-model:value="answerDrafts[activeAnswer.id]"
                :disabled="!!activeAnswer.answered_at || activeSession.status !== 'in_progress'"
              >
                <NRadio value="TRUE">正确</NRadio>
                <NRadio value="FALSE">错误</NRadio>
              </NRadioGroup>

              <NInput
                v-else
                v-model:value="answerDrafts[activeAnswer.id]"
                type="textarea"
                placeholder="请输入答案"
                :autosize="{ minRows: 5, maxRows: 10 }"
                :disabled="!!activeAnswer.answered_at || activeSession.status !== 'in_progress'"
              />
            </div>

            <div v-if="activeAnswer.reveal_answer" class="exam-practice-result">
              <div><strong>我的答案：</strong>{{ renderAnswerValue(activeAnswer) }}</div>
              <div><strong>正确答案：</strong>{{ renderCorrectAnswer(activeAnswer) }}</div>
              <div v-if="activeAnswer.answer_snapshot?.analysis">
                <strong>解析：</strong>{{ activeAnswer.answer_snapshot.analysis }}
              </div>
            </div>

            <div class="exam-practice-card-actions">
              <NButton
                v-if="!activeAnswer.answered_at && activeSession.status === 'in_progress'"
                type="primary"
                @click="submitCurrentAnswer"
              >
                提交并看答案
              </NButton>
              <NButton
                secondary
                type="primary"
                :disabled="activeAnswerIndex >= activeSession.answers.length - 1"
                @click="goNextAnswer"
              >
                下一题
              </NButton>
            </div>
          </section>
        </NLayoutContent>
      </NLayout>
    </NSpin>

    <NModal
      v-model:show="selectorVisible"
      preset="card"
      title="选择题目"
      style="width: 1180px"
      :mask-closable="false"
    >
      <div class="exam-practice-selector-query">
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

      <div class="exam-practice-selector-tools">
        <div class="exam-practice-random-picker">
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
          <NButton type="primary" @click="handleConfirmSelectQuestions">加入练习</NButton>
        </div>
      </template>
    </NModal>
  </CommonPage>
</template>

<style scoped lang="scss">
.exam-practice-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
}

.exam-practice-home,
.exam-practice-layout {
  --exam-practice-bg: #fff;
  --exam-practice-fill: #f8fafc;
  --exam-practice-border: #e5e7eb;
  --exam-practice-text: #111827;
  --exam-practice-muted: #64748b;
  --exam-practice-active-bg: #eff6ff;
  --exam-practice-active-border: #2563eb;
  --exam-practice-active-text: #1d4ed8;
  --exam-practice-done-bg: #fff7ed;
  --exam-practice-done-border: #fdba74;
  --exam-practice-done-text: #ea580c;

  color: var(--exam-practice-text);
}

.exam-practice-home.is-dark,
.exam-practice-layout.is-dark {
  --exam-practice-bg: #000;
  --exam-practice-fill: #18191d;
  --exam-practice-border: #2a2b30;
  --exam-practice-text: rgba(255, 255, 255, 0.88);
  --exam-practice-muted: rgba(255, 255, 255, 0.62);
  --exam-practice-active-bg: rgba(37, 99, 235, 0.2);
  --exam-practice-active-border: #60a5fa;
  --exam-practice-active-text: #93c5fd;
  --exam-practice-done-bg: rgba(244, 81, 30, 0.14);
  --exam-practice-done-border: rgba(244, 81, 30, 0.55);
  --exam-practice-done-text: #ff8a4c;
}

.exam-practice-home {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.exam-practice-start,
.exam-practice-history {
  padding: 18px 20px;
  border: 1px solid var(--exam-practice-border);
  border-radius: 8px;
  background: var(--exam-practice-bg);
}

.exam-practice-start {
  h2 {
    margin: 0;
    font-size: 22px;
    font-weight: 600;
  }

  p {
    margin: 8px 0 0;
    color: var(--exam-practice-muted);
    line-height: 1.7;
  }
}

.exam-practice-start-header,
.exam-practice-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
}

.exam-practice-start-header {
  margin-bottom: 18px;
}

.exam-practice-question-wrap {
  width: 100%;
}

.exam-practice-toolbar {
  margin-bottom: 14px;
  color: var(--exam-practice-muted);
}

.exam-practice-toolbar-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.exam-practice-question-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.exam-practice-question-card {
  padding: 14px 16px;
  border: 1px solid var(--exam-practice-border);
  border-radius: 8px;
  background: var(--exam-practice-fill);

  header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    gap: 12px;
    margin-bottom: 10px;
  }

  header > div {
    display: flex;
    align-items: center;
    gap: 8px;
    flex-wrap: wrap;
  }

  p {
    margin: 0 0 10px;
    line-height: 1.7;
    color: var(--exam-practice-text);
  }
}

.exam-practice-question-meta {
  display: flex;
  gap: 18px;
  flex-wrap: wrap;
  color: var(--exam-practice-muted);
  font-size: 13px;
}

.exam-practice-empty {
  padding: 28px 16px;
  border: 1px dashed var(--exam-practice-border);
  border-radius: 8px;
  color: var(--exam-practice-muted);
  text-align: center;
}

.exam-practice-history header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;

  h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }
}

.exam-practice-history-actions {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  flex-wrap: wrap;
}

.exam-practice-layout {
  height: calc(100vh - 260px);
  min-height: 540px;
  overflow: hidden;
  background: var(--exam-practice-bg);
}

.exam-practice-sider {
  height: 100%;
  background: var(--exam-practice-bg);

  :deep(.n-layout-sider-scroll-container) {
    height: 100%;
    background: var(--exam-practice-bg);
  }
}

.exam-practice-summary {
  padding: 12px 14px;
  border-radius: 8px;
  background: var(--exam-practice-fill);
  color: var(--exam-practice-muted);
  line-height: 1.8;
  margin-bottom: 16px;

  p {
    margin: 0;
  }
}

.exam-practice-nav {
  display: flex;
  flex-direction: column;
  gap: 8px;
  height: calc(100% - 136px);
  overflow-y: auto;
  padding-right: 4px;
}

.exam-practice-nav-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--exam-practice-border);
  border-radius: 8px;
  background: var(--exam-practice-bg);
  color: var(--exam-practice-text);
  text-align: left;
  cursor: pointer;

  &.answered {
    border-color: var(--exam-practice-done-border);
    background: var(--exam-practice-done-bg);
    color: var(--exam-practice-done-text);
  }

  &.correct {
    border-color: #86efac;
  }

  &.wrong {
    border-color: #fca5a5;
  }

  &.active {
    border-color: var(--exam-practice-active-border);
    background: var(--exam-practice-active-bg);
    color: var(--exam-practice-active-text);
  }

  small {
    color: var(--exam-practice-muted);
  }
}

.exam-practice-content {
  padding: 0 0 0 18px;
  overflow-y: auto;
}

.exam-practice-card {
  padding: 18px 20px;
  border: 1px solid var(--exam-practice-border);
  border-radius: 8px;
  background: var(--exam-practice-bg);
}

.exam-practice-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 16px;

  h3 {
    margin: 0 0 8px;
    font-size: 20px;
    font-weight: 600;
  }
}

.exam-practice-stem {
  margin: 0 0 14px;
  color: var(--exam-practice-text);
  line-height: 1.8;
}

.exam-practice-answer {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.exam-practice-answer :deep(.n-radio-group),
.exam-practice-answer :deep(.n-checkbox-group) {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.exam-practice-answer :deep(.n-radio),
.exam-practice-answer :deep(.n-checkbox) {
  width: 100%;
  min-height: 48px;
  box-sizing: border-box;
  padding: 12px 14px;
  border: 1px solid var(--exam-practice-border);
  border-radius: 8px;
  background: var(--exam-practice-fill);
}

.exam-practice-answer :deep(.n-radio__label),
.exam-practice-answer :deep(.n-checkbox__label) {
  color: var(--exam-practice-text);
}

.exam-practice-result {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 14px 16px;
  border-radius: 8px;
  background: var(--exam-practice-fill);
  color: var(--exam-practice-text);
  line-height: 1.8;
  margin-top: 16px;
}

.exam-practice-card-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  margin-top: 18px;
}

.exam-practice-selector-query {
  display: grid;
  grid-template-columns: repeat(5, minmax(0, 1fr));
  gap: 12px;
  margin-bottom: 16px;
}

.exam-practice-selector-tools {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 16px;
  color: #64748b;
  flex-wrap: wrap;
}

.exam-practice-random-picker {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

@media (max-width: 960px) {
  .exam-practice-layout {
    display: flex;
    flex-direction: column;
    height: auto;
    min-height: 0;
    overflow: visible;
  }

  .exam-practice-sider {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 100% !important;
  }

  .exam-practice-nav {
    max-height: 52vh;
  }

  .exam-practice-content {
    padding: 16px 0 0;
    overflow: visible;
  }

  .exam-practice-selector-query {
    grid-template-columns: 1fr;
  }
}
</style>
