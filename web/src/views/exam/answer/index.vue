<script setup>
import { h, nextTick, onMounted, ref } from 'vue'
import {
  NButton,
  NCheckbox,
  NCheckboxGroup,
  NDataTable,
  NEmpty,
  NInput,
  NRadio,
  NRadioGroup,
  NSpin,
  NTag,
  NTabs,
  NTabPane,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import examApi from '@/api/exam'
import { useAppStore } from '@/store'
import { formatDate } from '@/utils'

import {
  ATTEMPT_STATUS_LABEL_MAP,
  JUDGE_STATUS_LABEL_MAP,
  QUESTION_TYPE_LABEL_MAP,
  trueFalseOptions,
} from '../constants'

defineOptions({ name: '我的答题' })

const appStore = useAppStore()
const loading = ref(false)
const activeTab = ref('papers')
const searchTitle = ref('')
const availablePapers = ref([])
const myAttempts = ref([])
const activeAttempt = ref(null)
const saving = ref(false)
const submitting = ref(false)

onMounted(async () => {
  await loadLists()
})

async function loadLists() {
  loading.value = true
  try {
    const [paperRes, attemptRes] = await Promise.all([
      examApi.getAnswerableExamPaperList({
        page: 1,
        page_size: 9999,
        title: searchTitle.value || undefined,
      }),
      examApi.getMyExamAttemptList({
        page: 1,
        page_size: 9999,
        title: searchTitle.value || undefined,
      }),
    ])
    availablePapers.value = paperRes.data
    myAttempts.value = attemptRes.data
  } finally {
    loading.value = false
  }
}

function normalizeAttemptDetail(data) {
  return {
    ...data,
    answers: (data.answers || []).map((item) => {
      const questionType = item.question_type
      let answerValue = ''
      if (questionType === 'multiple_choice') {
        answerValue = Array.isArray(item.answer_payload) ? [...item.answer_payload] : []
      } else if (questionType === 'single_choice' || questionType === 'true_false') {
        answerValue = Array.isArray(item.answer_payload)
          ? item.answer_payload[0] || null
          : item.answer_payload || null
      } else {
        answerValue = typeof item.answer_payload === 'string' ? item.answer_payload : ''
      }
      return {
        ...item,
        answer_value: answerValue,
      }
    }),
  }
}

function serializeAttemptAnswers() {
  return (activeAttempt.value?.answers || []).map((item) => {
    let answerPayload = item.answer_value
    if (item.question_type === 'multiple_choice') {
      answerPayload = Array.isArray(item.answer_value) ? [...item.answer_value] : []
    } else if (item.question_type === 'single_choice' || item.question_type === 'true_false') {
      answerPayload = item.answer_value ? [item.answer_value] : []
    } else {
      answerPayload = item.answer_value || ''
    }
    return {
      paper_question_id: item.paper_question_id,
      answer_payload: answerPayload,
    }
  })
}

async function openAttemptByPaper(row) {
  if (row.attempt?.id) {
    const { data } = await examApi.getMyExamAttemptById({ attempt_id: row.attempt.id })
    activeAttempt.value = normalizeAttemptDetail(data)
    return
  }

  const { data } = await examApi.startExamAttempt({ paper_id: row.id })
  activeAttempt.value = normalizeAttemptDetail(data)
}

async function openAttemptDetail(row) {
  const { data } = await examApi.getMyExamAttemptById({ attempt_id: row.id })
  activeAttempt.value = normalizeAttemptDetail(data)
}

async function handleSaveAttempt() {
  if (!activeAttempt.value?.can_submit) return
  saving.value = true
  try {
    const { data } = await examApi.saveExamAttempt({
      attempt_id: activeAttempt.value.id,
      answers: serializeAttemptAnswers(),
    })
    activeAttempt.value = normalizeAttemptDetail(data)
    await loadLists()
    $message.success('答卷已暂存')
  } finally {
    saving.value = false
  }
}

async function handleSubmitAttempt() {
  if (!activeAttempt.value?.can_submit) return
  const confirmed = window.confirm('提交后将不能再修改答案，确认提交吗？')
  if (!confirmed) return

  submitting.value = true
  try {
    const { data } = await examApi.submitExamAttempt({
      attempt_id: activeAttempt.value.id,
      answers: serializeAttemptAnswers(),
    })
    activeAttempt.value = normalizeAttemptDetail(data)
    await loadLists()
    $message.success(data.status === 'graded' ? '提交成功，已完成判题' : '提交成功，等待人工阅卷')
  } finally {
    submitting.value = false
  }
}

async function goBackToList() {
  activeAttempt.value = null
  await nextTick()
  await loadLists()
}

function renderAttemptStatus(status) {
  const type = status === 'graded' ? 'success' : status === 'pending_review' ? 'warning' : 'info'
  return h(NTag, { type }, { default: () => ATTEMPT_STATUS_LABEL_MAP[status] || status })
}

function getAttemptActionLabel(row) {
  if (!row.attempt) return '开始答题'
  if (row.attempt.status === 'in_progress') return '继续答题'
  return '查看结果'
}

function findOptionLabel(snapshot, value) {
  if (value === 'TRUE') return '正确'
  if (value === 'FALSE') return '错误'
  const option = (snapshot.options || []).find((item) => item.option_key === value)
  return option ? `${option.option_key}. ${option.option_content}` : value
}

function renderAnswerText(answer) {
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
  const correctAnswer = answer.answer_snapshot?.correct_answer || []
  if (answer.question_type === 'multiple_choice') {
    return correctAnswer.map((item) => findOptionLabel(answer.answer_snapshot, item)).join('、')
  }
  if (answer.question_type === 'single_choice' || answer.question_type === 'true_false') {
    return correctAnswer.length ? findOptionLabel(answer.answer_snapshot, correctAnswer[0]) : '-'
  }
  return answer.answer_snapshot?.reference_answer || '-'
}

const paperColumns = [
  {
    title: '试卷标题',
    key: 'title',
    ellipsis: { tooltip: true },
  },
  {
    title: '总分',
    key: 'total_score',
    width: 80,
    align: 'center',
  },
  {
    title: '限时',
    key: 'duration_minutes',
    width: 90,
    align: 'center',
    render(row) {
      return `${row.duration_minutes || 0} 分钟`
    },
  },
  {
    title: '作答状态',
    key: 'attempt.status',
    width: 110,
    align: 'center',
    render(row) {
      return row.attempt ? renderAttemptStatus(row.attempt.status) : h('span', '未开始')
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 110,
    align: 'center',
    render(row) {
      return h(
        NButton,
        {
          size: 'small',
          type: 'primary',
          onClick: () => openAttemptByPaper(row),
        },
        { default: () => getAttemptActionLabel(row) }
      )
    },
  },
]

const attemptColumns = [
  {
    title: '试卷标题',
    key: 'paper.title',
    ellipsis: { tooltip: true },
    render(row) {
      return row.paper?.title || '-'
    },
  },
  {
    title: '状态',
    key: 'status',
    width: 110,
    align: 'center',
    render(row) {
      return renderAttemptStatus(row.status)
    },
  },
  {
    title: '总分',
    key: 'total_score',
    width: 80,
    align: 'center',
  },
  {
    title: '提交时间',
    key: 'submitted_at',
    width: 140,
    align: 'center',
    render(row) {
      return h('span', row.submitted_at ? formatDate(row.submitted_at, 'YYYY-MM-DD HH:mm:ss') : '-')
    },
  },
  {
    title: '操作',
    key: 'actions',
    width: 110,
    align: 'center',
    render(row) {
      return h(
        NButton,
        {
          size: 'small',
          type: 'primary',
          onClick: () => openAttemptDetail(row),
        },
        { default: () => (row.status === 'in_progress' ? '继续答题' : '查看结果') }
      )
    },
  },
]
</script>

<template>
  <CommonPage show-footer :title="activeAttempt ? '答题详情' : '我的答题'">
    <template #header>
      <div class="exam-answer-header" :class="{ 'is-dark': appStore.isDark }">
        <div>
          <h2>{{ activeAttempt ? activeAttempt.paper?.title || '答题详情' : '我的答题' }}</h2>
          <p v-if="activeAttempt">
            状态：{{ ATTEMPT_STATUS_LABEL_MAP[activeAttempt.status] || activeAttempt.status }}，
            总分：{{ activeAttempt.total_score }}
          </p>
          <p v-else>查看可答试卷、继续作答并跟踪阅卷结果</p>
        </div>
        <div class="exam-answer-header-actions">
          <template v-if="activeAttempt">
            <NButton @click="goBackToList">返回列表</NButton>
            <NButton v-if="activeAttempt.can_submit" :loading="saving" @click="handleSaveAttempt"
              >暂存答卷</NButton
            >
            <NButton
              v-if="activeAttempt.can_submit"
              type="primary"
              :loading="submitting"
              @click="handleSubmitAttempt"
            >
              提交答卷
            </NButton>
          </template>
          <template v-else>
            <NInput
              v-model:value="searchTitle"
              clearable
              placeholder="请输入试卷标题"
              class="exam-answer-search"
              @keypress.enter="loadLists"
            />
            <NButton type="primary" @click="loadLists">搜索</NButton>
          </template>
        </div>
      </div>
    </template>

    <NSpin :show="loading || saving || submitting">
      <div v-if="!activeAttempt">
        <NTabs v-model:value="activeTab" type="line" animated>
          <NTabPane name="papers" tab="可答试卷">
            <NEmpty v-if="!availablePapers.length" description="暂无可答试卷" />
            <NDataTable
              v-else
              :columns="paperColumns"
              :data="availablePapers"
              :pagination="false"
              :row-key="(row) => row.id"
            />
          </NTabPane>
          <NTabPane name="attempts" tab="我的记录">
            <NEmpty v-if="!myAttempts.length" description="暂无答卷记录" />
            <NDataTable
              v-else
              :columns="attemptColumns"
              :data="myAttempts"
              :pagination="false"
              :row-key="(row) => row.id"
            />
          </NTabPane>
        </NTabs>
      </div>

      <div v-else class="exam-attempt-detail" :class="{ 'is-dark': appStore.isDark }">
        <section
          v-for="(item, index) in activeAttempt.answers"
          :key="item.id"
          class="exam-attempt-card"
        >
          <header class="exam-attempt-card-header">
            <div class="exam-attempt-card-title">
              <h3>第 {{ index + 1 }} 题</h3>
              <NTag type="info" :bordered="false">
                {{ QUESTION_TYPE_LABEL_MAP[item.question_type] || item.question_type }}
              </NTag>
            </div>
            <div class="exam-attempt-card-meta">
              <span>本题分值：{{ item.answer_snapshot?.score || 0 }}</span>
              <NTag v-if="item.judge_status" size="small" :bordered="false" type="info">
                {{ JUDGE_STATUS_LABEL_MAP[item.judge_status] || item.judge_status }}
              </NTag>
            </div>
          </header>

          <p class="exam-attempt-stem">{{ item.answer_snapshot?.stem }}</p>

          <div v-if="item.question_type === 'single_choice'" class="exam-attempt-answer">
            <NRadioGroup v-model:value="item.answer_value" :disabled="!activeAttempt.can_submit">
              <div
                v-for="option in item.answer_snapshot?.options || []"
                :key="option.option_key"
                class="exam-attempt-option"
              >
                <NRadio :value="option.option_key">
                  {{ option.option_key }}. {{ option.option_content }}
                </NRadio>
              </div>
            </NRadioGroup>
          </div>

          <div v-else-if="item.question_type === 'multiple_choice'" class="exam-attempt-answer">
            <NCheckboxGroup v-model:value="item.answer_value" :disabled="!activeAttempt.can_submit">
              <div
                v-for="option in item.answer_snapshot?.options || []"
                :key="option.option_key"
                class="exam-attempt-option"
              >
                <NCheckbox :value="option.option_key">
                  {{ option.option_key }}. {{ option.option_content }}
                </NCheckbox>
              </div>
            </NCheckboxGroup>
          </div>

          <div v-else-if="item.question_type === 'true_false'" class="exam-attempt-answer">
            <NRadioGroup v-model:value="item.answer_value" :disabled="!activeAttempt.can_submit">
              <div
                v-for="option in trueFalseOptions"
                :key="option.value"
                class="exam-attempt-option"
              >
                <NRadio :value="option.value">{{ option.label }}</NRadio>
              </div>
            </NRadioGroup>
          </div>

          <div v-else-if="item.question_type === 'fill_blank'" class="exam-attempt-answer">
            <NInput
              v-model:value="item.answer_value"
              :disabled="!activeAttempt.can_submit"
              placeholder="请输入答案"
            />
          </div>

          <div v-else class="exam-attempt-answer">
            <NInput
              v-model:value="item.answer_value"
              :disabled="!activeAttempt.can_submit"
              type="textarea"
              placeholder="请输入答案"
              :autosize="{ minRows: 5, maxRows: 10 }"
            />
          </div>

          <div v-if="activeAttempt.show_result" class="exam-attempt-result">
            <div><strong>我的答案：</strong>{{ renderAnswerText(item) }}</div>
            <div><strong>参考答案：</strong>{{ renderCorrectAnswer(item) }}</div>
            <div v-if="item.answer_snapshot?.analysis">
              <strong>解析：</strong>{{ item.answer_snapshot.analysis }}
            </div>
            <div><strong>得分：</strong>{{ item.final_score }}</div>
          </div>
        </section>
      </div>
    </NSpin>
  </CommonPage>
</template>

<style scoped lang="scss">
.exam-answer-header {
  --exam-answer-text: var(--n-text-color, #111827);
  --exam-answer-text-muted: var(--n-text-color-2, #64748b);

  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;

  h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
    color: var(--exam-answer-text);
  }

  p {
    margin: 6px 0 0;
    color: var(--exam-answer-text-muted);
    line-height: 1.7;
  }
}

.exam-answer-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.exam-answer-search {
  width: 260px;
}

.exam-attempt-detail {
  --exam-answer-card-bg: #fff;
  --exam-answer-fill: #f8fafc;
  --exam-answer-border: #e5e7eb;
  --exam-answer-text: #111827;
  --exam-answer-text-muted: #64748b;
  --exam-answer-result-bg: #eff6ff;
  --exam-answer-result-text: #1e3a8a;
  --exam-answer-accent: #f4511e;

  display: flex;
  flex-direction: column;
  gap: 16px;
}

.exam-attempt-card {
  padding: 22px 24px;
  border: 1px solid var(--exam-answer-border);
  border-radius: 8px;
  background: var(--exam-answer-card-bg);
  color: var(--exam-answer-text);
}

.exam-attempt-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 18px;
}

.exam-attempt-card-title {
  display: flex;
  align-items: center;
  gap: 10px;

  h3 {
    margin: 0;
    font-size: 18px;
    font-weight: 600;
  }
}

.exam-attempt-card-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--exam-answer-text-muted);
}

.exam-attempt-stem {
  margin: 0 0 18px;
  line-height: 1.8;
  color: var(--exam-answer-text);
}

.exam-attempt-answer {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.exam-attempt-option {
  padding: 14px 16px;
  border: 1px solid var(--exam-answer-border);
  border-radius: 8px;
  background: var(--exam-answer-fill);
}

.exam-attempt-option :deep(.n-radio__label),
.exam-attempt-option :deep(.n-checkbox__label) {
  color: var(--exam-answer-text);
}

.exam-attempt-result {
  margin-top: 20px;
  padding: 14px 16px;
  border: 1px solid var(--exam-answer-border);
  border-left: 3px solid var(--exam-answer-accent);
  border-radius: 8px;
  background: var(--exam-answer-result-bg);
  color: var(--exam-answer-result-text);
  line-height: 1.8;
}

.exam-answer-header.is-dark {
  --exam-answer-text: rgba(255, 255, 255, 0.9);
  --exam-answer-text-muted: rgba(255, 255, 255, 0.64);
}

.exam-attempt-detail.is-dark {
  --exam-answer-card-bg: #000;
  --exam-answer-fill: #18191d;
  --exam-answer-border: #2a2b30;
  --exam-answer-text: rgba(255, 255, 255, 0.9);
  --exam-answer-text-muted: rgba(255, 255, 255, 0.64);
  --exam-answer-result-bg: #111217;
  --exam-answer-result-text: rgba(255, 255, 255, 0.86);
}

@media (max-width: 768px) {
  .exam-answer-search {
    width: 100%;
  }
}
</style>
