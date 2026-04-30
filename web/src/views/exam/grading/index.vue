<script setup>
import { computed, h, nextTick, onMounted, ref } from 'vue'
import {
  NButton,
  NDataTable,
  NEmpty,
  NInput,
  NInputNumber,
  NLayout,
  NLayoutContent,
  NLayoutSider,
  NSelect,
  NSpin,
  NTag,
} from 'naive-ui'

import CommonPage from '@/components/page/CommonPage.vue'
import examApi from '@/api/exam'
import { useAppStore, useUserStore } from '@/store'
import { formatDate } from '@/utils'

import {
  ATTEMPT_STATUS_LABEL_MAP,
  JUDGE_STATUS_LABEL_MAP,
  QUESTION_TYPE_LABEL_MAP,
  attemptStatusOptions,
} from '../constants'

defineOptions({ name: '阅卷中心' })

const appStore = useAppStore()
const userStore = useUserStore()
const loading = ref(false)
const detailLoading = ref(false)
const gradingList = ref([])
const activeAttempt = ref(null)
const activeAnswerIndex = ref(0)
const queryItems = ref({
  paper_title: '',
  username: '',
  status: 'pending_review',
})

onMounted(async () => {
  await loadGradingList()
})

async function loadGradingList() {
  loading.value = true
  try {
    const { data } = await examApi.getExamGradingList({
      page: 1,
      page_size: 9999,
      ...queryItems.value,
    })
    gradingList.value = data
  } finally {
    loading.value = false
  }
}

function normalizeGradingDetail(data) {
  return {
    ...data,
    answers: (data.answers || []).map((item) => ({
      ...item,
      manual_score_input: item.manual_score || 0,
      reviewer_comment_input: item.reviewer_comment || '',
    })),
  }
}

async function openGradingDetail(row) {
  detailLoading.value = true
  try {
    const { data } = await examApi.getExamGradingDetail({ attempt_id: row.id })
    activeAttempt.value = normalizeGradingDetail(data)
    activeAnswerIndex.value = 0
  } finally {
    detailLoading.value = false
  }
}

async function goBack() {
  activeAttempt.value = null
  await nextTick()
  await loadGradingList()
}

const activeAnswer = computed(() => {
  return activeAttempt.value?.answers?.[activeAnswerIndex.value] || null
})

const canGradeActiveAttempt = computed(() => {
  return (
    activeAttempt.value?.status === 'pending_review' && isAttemptClaimedByMe(activeAttempt.value)
  )
})

function isAttemptClaimed(attempt) {
  return Boolean(attempt?.claimed_by)
}

function isAttemptClaimedByMe(attempt) {
  return Boolean(attempt?.claimed_by) && Number(attempt.claimed_by) === Number(userStore.userId)
}

function isAttemptClaimedByOther(attempt) {
  return isAttemptClaimed(attempt) && !isAttemptClaimedByMe(attempt)
}

function renderClaimName(attempt) {
  return attempt?.claimed_by_name || (attempt?.claimed_by ? `用户 ${attempt.claimed_by}` : '未领取')
}

function renderStatus(status) {
  const type = status === 'graded' ? 'success' : status === 'pending_review' ? 'warning' : 'info'
  return h(NTag, { type }, { default: () => ATTEMPT_STATUS_LABEL_MAP[status] || status })
}

function renderClaimStatus(row) {
  const props = isAttemptClaimed(row) ? { type: 'warning', bordered: false } : { bordered: false }
  return h(NTag, props, { default: () => renderClaimName(row) })
}

function getGradingRowClass(row) {
  return isAttemptClaimed(row) ? 'exam-grading-row-claimed' : ''
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
  if (!answer) return '-'
  const correctAnswer = answer.answer_snapshot?.correct_answer || []
  if (answer.question_type === 'multiple_choice') {
    return correctAnswer.map((item) => findOptionLabel(answer.answer_snapshot, item)).join('、')
  }
  if (answer.question_type === 'single_choice' || answer.question_type === 'true_false') {
    return correctAnswer.length ? findOptionLabel(answer.answer_snapshot, correctAnswer[0]) : '-'
  }
  return answer.answer_snapshot?.reference_answer || '-'
}

function isSubjective(answer) {
  return ['fill_blank', 'short_answer'].includes(answer?.question_type)
}

function isAnswerJudged(answer) {
  return ['auto_correct', 'auto_wrong', 'manual_done'].includes(answer?.judge_status)
}

async function handleScoreAnswer(answer) {
  await examApi.scoreExamAnswer({
    answer_id: answer.id,
    manual_score: Number(answer.manual_score_input || 0),
    reviewer_comment: answer.reviewer_comment_input || '',
  })
  const { data } = await examApi.getExamGradingDetail({ attempt_id: activeAttempt.value.id })
  activeAttempt.value = normalizeGradingDetail(data)
  $message.success('评分已保存')
  await loadGradingList()
}

async function refreshActiveAttempt() {
  if (!activeAttempt.value?.id) return
  const { data } = await examApi.getExamGradingDetail({ attempt_id: activeAttempt.value.id })
  activeAttempt.value = normalizeGradingDetail(data)
}

async function handleClaimGrading(attempt) {
  const { data } = await examApi.claimExamGrading({ attempt_id: attempt.id })
  if (activeAttempt.value?.id === attempt.id) {
    activeAttempt.value = normalizeGradingDetail(data)
  }
  await loadGradingList()
  $message.success('领取成功')
}

async function handleReleaseGrading(attempt) {
  const { data } = await examApi.releaseExamGrading({ attempt_id: attempt.id })
  if (activeAttempt.value?.id === attempt.id) {
    activeAttempt.value = normalizeGradingDetail(data)
  }
  await loadGradingList()
  $message.success('释放成功')
}

async function handleCompleteGrading() {
  await examApi.completeExamGrading({ attempt_id: activeAttempt.value.id })
  await refreshActiveAttempt()
  await loadGradingList()
  $message.success('阅卷完成')
}

const columns = [
  {
    title: '试卷标题',
    key: 'paper.title',
    ellipsis: { tooltip: true },
    render(row) {
      return row.paper?.title || '-'
    },
  },
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
    width: 110,
    align: 'center',
    render(row) {
      return renderStatus(row.status)
    },
  },
  {
    title: '领取人',
    key: 'claimed_by_name',
    width: 120,
    align: 'center',
    render(row) {
      return renderClaimStatus(row)
    },
  },
  {
    title: '客观题得分',
    key: 'objective_score',
    width: 110,
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
    width: 220,
    align: 'center',
    render(row) {
      const isPending = row.status === 'pending_review'
      return h('div', { class: 'exam-grading-table-actions' }, [
        isPending
          ? h(
              NButton,
              {
                size: 'small',
                type: 'primary',
                secondary: true,
                disabled: isAttemptClaimedByMe(row) || isAttemptClaimedByOther(row),
                onClick: () => handleClaimGrading(row),
              },
              { default: () => '领取' }
            )
          : null,
        isPending && isAttemptClaimedByMe(row)
          ? h(
              NButton,
              {
                size: 'small',
                secondary: true,
                onClick: () => handleReleaseGrading(row),
              },
              { default: () => '释放' }
            )
          : null,
        h(
          NButton,
          {
            size: 'small',
            type: row.status === 'graded' ? 'default' : 'primary',
            disabled: isPending && !isAttemptClaimedByMe(row),
            onClick: () => openGradingDetail(row),
          },
          { default: () => (row.status === 'graded' ? '查看' : '阅卷') }
        ),
      ])
    },
  },
]
</script>

<template>
  <CommonPage show-footer :title="activeAttempt ? '阅卷详情' : '阅卷中心'">
    <template #header>
      <div class="exam-grading-header" :class="{ 'is-dark': appStore.isDark }">
        <div>
          <h2>{{ activeAttempt ? activeAttempt.paper?.title || '阅卷详情' : '阅卷中心' }}</h2>
          <p v-if="activeAttempt">
            答题人：{{ activeAttempt.user?.username || '-' }}， 状态：{{
              ATTEMPT_STATUS_LABEL_MAP[activeAttempt.status] || activeAttempt.status
            }}， 领取人：{{ renderClaimName(activeAttempt) }}
          </p>
          <p v-else>按试卷和答题人筛选待阅卷任务，逐题完成人工评分</p>
        </div>
        <div class="exam-grading-header-actions">
          <template v-if="activeAttempt">
            <NButton @click="goBack">返回列表</NButton>
            <NButton
              v-if="activeAttempt.status === 'pending_review'"
              type="primary"
              secondary
              :disabled="isAttemptClaimed(activeAttempt)"
              @click="handleClaimGrading(activeAttempt)"
            >
              领取
            </NButton>
            <NButton
              v-if="
                activeAttempt.status === 'pending_review' && isAttemptClaimedByMe(activeAttempt)
              "
              secondary
              @click="handleReleaseGrading(activeAttempt)"
            >
              释放
            </NButton>
            <NButton
              v-if="activeAttempt.status === 'pending_review'"
              type="primary"
              :disabled="!canGradeActiveAttempt"
              @click="handleCompleteGrading"
            >
              完成阅卷
            </NButton>
          </template>
          <template v-else>
            <NInput
              v-model:value="queryItems.paper_title"
              clearable
              placeholder="试卷标题"
              class="exam-grading-search"
              @keypress.enter="loadGradingList"
            />
            <NInput
              v-model:value="queryItems.username"
              clearable
              placeholder="答题人"
              class="exam-grading-search"
              @keypress.enter="loadGradingList"
            />
            <NSelect
              v-model:value="queryItems.status"
              :options="attemptStatusOptions"
              class="exam-grading-status"
            />
            <NButton type="primary" @click="loadGradingList">搜索</NButton>
          </template>
        </div>
      </div>
    </template>

    <NSpin :show="loading || detailLoading">
      <div v-if="!activeAttempt">
        <NEmpty v-if="!gradingList.length" description="暂无阅卷任务" />
        <NDataTable
          v-else
          :columns="columns"
          :data="gradingList"
          :pagination="false"
          :row-class-name="getGradingRowClass"
          :row-key="(row) => row.id"
        />
      </div>

      <NLayout v-else has-sider class="exam-grading-layout" :class="{ 'is-dark': appStore.isDark }">
        <NLayoutSider
          bordered
          content-style="padding: 18px 10px 18px 14px; height: 100%;"
          :width="230"
          class="exam-grading-sider"
        >
          <div class="exam-grading-sider-inner">
            <div class="exam-grading-summary">
              <p>客观题得分：{{ activeAttempt.objective_score }}</p>
              <p>主观题得分：{{ activeAttempt.subjective_score }}</p>
              <p>当前总分：{{ activeAttempt.total_score }}</p>
              <p>领取人：{{ renderClaimName(activeAttempt) }}</p>
            </div>

            <div class="exam-grading-nav">
              <button
                v-for="(item, index) in activeAttempt.answers"
                :key="item.id"
                type="button"
                :class="[
                  'exam-grading-nav-item',
                  {
                    active: index === activeAnswerIndex,
                    judged: isAnswerJudged(item),
                  },
                ]"
                @click="activeAnswerIndex = index"
              >
                <span>第 {{ index + 1 }} 题</span>
                <small>
                  {{ QUESTION_TYPE_LABEL_MAP[item.question_type] || item.question_type }}
                </small>
              </button>
            </div>
          </div>
        </NLayoutSider>

        <NLayoutContent class="exam-grading-content">
          <section v-if="activeAnswer" class="exam-grading-card">
            <header class="exam-grading-card-header">
              <div>
                <h3>第 {{ activeAnswerIndex + 1 }} 题</h3>
                <NTag type="info" :bordered="false">
                  {{
                    QUESTION_TYPE_LABEL_MAP[activeAnswer.question_type] ||
                    activeAnswer.question_type
                  }}
                </NTag>
              </div>
              <div class="exam-grading-card-meta">
                <span>本题分值：{{ activeAnswer.answer_snapshot?.score || 0 }}</span>
                <NTag size="small" type="warning">{{
                  JUDGE_STATUS_LABEL_MAP[activeAnswer.judge_status] || activeAnswer.judge_status
                }}</NTag>
              </div>
            </header>

            <p class="exam-grading-stem">{{ activeAnswer.answer_snapshot?.stem }}</p>

            <div v-if="activeAnswer.answer_snapshot?.options?.length" class="exam-grading-options">
              <div
                v-for="option in activeAnswer.answer_snapshot.options"
                :key="option.option_key"
                class="exam-grading-option"
              >
                {{ option.option_key }}. {{ option.option_content }}
              </div>
            </div>

            <div class="exam-grading-result-box">
              <div><strong>用户答案：</strong>{{ renderAnswerValue(activeAnswer) }}</div>
              <div><strong>参考答案：</strong>{{ renderCorrectAnswer(activeAnswer) }}</div>
              <div v-if="activeAnswer.answer_snapshot?.analysis">
                <strong>解析：</strong>{{ activeAnswer.answer_snapshot.analysis }}
              </div>
            </div>

            <div v-if="isSubjective(activeAnswer)" class="exam-grading-score-box">
              <NInputNumber
                v-model:value="activeAnswer.manual_score_input"
                :min="0"
                :max="activeAnswer.answer_snapshot?.score || 0"
                :precision="2"
                :disabled="!canGradeActiveAttempt"
              />
              <NInput
                v-model:value="activeAnswer.reviewer_comment_input"
                type="textarea"
                placeholder="请输入阅卷备注"
                :autosize="{ minRows: 4, maxRows: 8 }"
                :disabled="!canGradeActiveAttempt"
              />
              <NButton
                v-if="activeAttempt.status === 'pending_review'"
                type="primary"
                :disabled="!canGradeActiveAttempt"
                @click="handleScoreAnswer(activeAnswer)"
              >
                保存评分
              </NButton>
            </div>

            <div v-else class="exam-grading-result-box">
              <div><strong>自动得分：</strong>{{ activeAnswer.final_score }}</div>
            </div>
          </section>
        </NLayoutContent>
      </NLayout>
    </NSpin>
  </CommonPage>
</template>

<style scoped lang="scss">
.exam-grading-header {
  --exam-grading-header-title: #111827;
  --exam-grading-header-muted: #64748b;

  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 20px;
  flex-wrap: wrap;

  h2 {
    margin: 0;
    font-size: 24px;
    font-weight: 600;
    color: var(--exam-grading-header-title);
  }

  p {
    margin: 6px 0 0;
    color: var(--exam-grading-header-muted);
    line-height: 1.7;
  }
}

.exam-grading-header.is-dark {
  --exam-grading-header-title: rgba(255, 255, 255, 0.9);
  --exam-grading-header-muted: rgba(255, 255, 255, 0.64);
}

.exam-grading-header-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.exam-grading-search {
  width: 180px;
}

.exam-grading-status {
  width: 160px;
}

.exam-grading-table-actions {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
}

:deep(.exam-grading-row-claimed td) {
  background-color: rgba(244, 81, 30, 0.08) !important;
}

:deep(.exam-grading-row-claimed:hover td) {
  background-color: rgba(244, 81, 30, 0.14) !important;
}

.exam-grading-layout {
  --exam-grading-page-bg: #fff;
  --exam-grading-panel-bg: #fff;
  --exam-grading-card-bg: linear-gradient(180deg, #ffffff 0%, #fafaf9 100%);
  --exam-grading-fill-bg: #f8fafc;
  --exam-grading-option-bg: #fff;
  --exam-grading-border: #e5e7eb;
  --exam-grading-text: #111827;
  --exam-grading-muted: #64748b;
  --exam-grading-scrollbar: #d1d5db;
  --exam-grading-nav-bg: #fff;
  --exam-grading-nav-judged-bg: #fff7ed;
  --exam-grading-nav-judged-border: #fdba74;
  --exam-grading-nav-judged-text: #ea580c;
  --exam-grading-nav-judged-muted: #c2410c;
  --exam-grading-nav-active-bg: #eff6ff;
  --exam-grading-nav-active-border: #2563eb;
  --exam-grading-nav-active-text: #1d4ed8;
  --exam-grading-nav-judged-active-bg: #fff3eb;
  --exam-grading-nav-judged-active-border: var(--primary-color);
  --exam-grading-nav-judged-active-text: var(--primary-color);

  height: calc(100vh - 260px);
  min-height: 520px;
  overflow: hidden;
  background: var(--exam-grading-page-bg);
  color: var(--exam-grading-text);
}

.exam-grading-layout.is-dark {
  --exam-grading-page-bg: #101014;
  --exam-grading-panel-bg: #101014;
  --exam-grading-card-bg: #000;
  --exam-grading-fill-bg: #18191d;
  --exam-grading-option-bg: #18191d;
  --exam-grading-border: #2a2b30;
  --exam-grading-text: rgba(255, 255, 255, 0.88);
  --exam-grading-muted: rgba(255, 255, 255, 0.62);
  --exam-grading-scrollbar: #4b5563;
  --exam-grading-nav-bg: #18191d;
  --exam-grading-nav-judged-bg: rgba(244, 81, 30, 0.14);
  --exam-grading-nav-judged-border: rgba(244, 81, 30, 0.55);
  --exam-grading-nav-judged-text: #ff8a4c;
  --exam-grading-nav-judged-muted: #ffc2a8;
  --exam-grading-nav-active-bg: rgba(37, 99, 235, 0.2);
  --exam-grading-nav-active-border: #60a5fa;
  --exam-grading-nav-active-text: #93c5fd;
  --exam-grading-nav-judged-active-bg: rgba(244, 81, 30, 0.2);
  --exam-grading-nav-judged-active-border: #ff8a4c;
  --exam-grading-nav-judged-active-text: #ffb088;
}

.exam-grading-sider {
  height: 100%;
  background: var(--exam-grading-panel-bg);

  :deep(.n-layout-sider-scroll-container) {
    height: 100%;
    background: var(--exam-grading-panel-bg);
  }
}

.exam-grading-sider-inner {
  display: flex;
  flex-direction: column;
  height: 100%;
  min-height: 0;
}

.exam-grading-summary {
  flex: 0 0 auto;
  padding: 12px 14px;
  border-radius: 14px;
  background: var(--exam-grading-fill-bg);
  color: var(--exam-grading-muted);
  line-height: 1.8;
  margin-bottom: 16px;

  p {
    margin: 0;
  }
}

.exam-grading-nav {
  display: flex;
  flex-direction: column;
  flex: 1 1 auto;
  gap: 8px;
  min-height: 0;
  overflow-y: auto;
  padding-right: 4px;

  &::-webkit-scrollbar {
    width: 6px;
  }

  &::-webkit-scrollbar-thumb {
    border-radius: 3px;
    background: var(--exam-grading-scrollbar);
  }
}

.exam-grading-nav-item {
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  gap: 4px;
  padding: 12px 14px;
  border: 1px solid var(--exam-grading-border);
  border-radius: 14px;
  background: var(--exam-grading-nav-bg);
  color: var(--exam-grading-text);
  text-align: left;
  cursor: pointer;
  transition: border-color 0.2s ease, background-color 0.2s ease, color 0.2s ease,
    box-shadow 0.2s ease;

  &.judged {
    border-color: var(--exam-grading-nav-judged-border);
    background: var(--exam-grading-nav-judged-bg);
    color: var(--exam-grading-nav-judged-text);

    small {
      color: var(--exam-grading-nav-judged-muted);
    }
  }

  &.active {
    border-color: var(--exam-grading-nav-active-border);
    background: var(--exam-grading-nav-active-bg);
    color: var(--exam-grading-nav-active-text);
  }

  &.judged.active {
    border-color: var(--exam-grading-nav-judged-active-border);
    background: var(--exam-grading-nav-judged-active-bg);
    color: var(--exam-grading-nav-judged-active-text);
    box-shadow: 0 0 0 3px rgba(244, 81, 30, 0.12);

    small {
      color: var(--exam-grading-nav-judged-muted);
    }
  }

  small {
    color: var(--exam-grading-muted);
  }
}

.exam-grading-content {
  padding: 0 0 0 18px;
  overflow-y: auto;
}

.exam-grading-card {
  padding: 18px 20px;
  border: 1px solid var(--exam-grading-border);
  border-radius: 18px;
  background: var(--exam-grading-card-bg);
  color: var(--exam-grading-text);
}

.exam-grading-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  margin-bottom: 14px;

  h3 {
    margin: 0 0 8px;
    font-size: 20px;
    font-weight: 600;
  }
}

.exam-grading-card-meta {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
  color: var(--exam-grading-muted);
}

.exam-grading-stem {
  margin: 0 0 14px;
  line-height: 1.8;
  color: var(--exam-grading-text);
}

.exam-grading-options {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-bottom: 14px;
}

.exam-grading-option {
  padding: 12px 14px;
  border-radius: 14px;
  border: 1px solid var(--exam-grading-border);
  background: var(--exam-grading-option-bg);
  color: var(--exam-grading-text);
}

.exam-grading-result-box,
.exam-grading-score-box {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px 16px;
  border-radius: 14px;
  background: var(--exam-grading-fill-bg);
  color: var(--exam-grading-text);
  line-height: 1.8;
}

@media (max-width: 960px) {
  .exam-grading-search,
  .exam-grading-status {
    width: 100%;
  }

  .exam-grading-layout {
    display: flex;
    flex-direction: column;
    height: auto;
    min-height: 0;
    overflow: visible;
  }

  .exam-grading-sider {
    width: 100% !important;
    max-width: 100% !important;
    min-width: 100% !important;
  }

  .exam-grading-sider-inner {
    max-height: 60vh;
  }

  .exam-grading-content {
    padding: 16px 0 0;
    overflow: visible;
  }
}
</style>
