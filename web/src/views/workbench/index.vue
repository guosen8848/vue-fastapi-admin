<template>
  <AppPage :show-footer="false">
    <n-spin :show="loading">
      <div class="workbench-page" :class="{ 'is-dark': appStore.isDark }">
        <n-card class="dashboard-card hero-card" :bordered="false">
          <div class="hero-main">
            <div class="hero-user">
              <img class="hero-avatar" :src="userStore.avatar" />
              <div>
                <p class="hero-title">{{ roleTitle }}</p>
                <p class="hero-subtitle">{{ userStore.name }}，{{ roleSubtitle }}</p>
              </div>
            </div>
            <n-button type="primary" secondary @click="loadDashboard">
              <template #icon>
                <TheIcon icon="material-symbols:refresh-rounded" :size="18" />
              </template>
              刷新
            </n-button>
          </div>
        </n-card>

        <div class="stat-grid">
          <n-card
            v-for="item in statCards"
            :key="item.key"
            class="dashboard-card stat-card"
            :class="item.tone"
            :bordered="false"
          >
            <div class="stat-icon">
              <TheIcon :icon="item.icon" :size="24" />
            </div>
            <div>
              <p class="stat-value">{{ item.value }}</p>
              <p class="stat-label">{{ item.label }}</p>
            </div>
          </n-card>
        </div>

        <div class="content-grid">
          <n-card class="dashboard-card" :bordered="false">
            <template #header>
              <div class="card-title">
                <TheIcon :icon="primaryListIcon" :size="20" />
                {{ primaryListTitle }}
              </div>
            </template>
            <div v-if="primaryRows.length" class="row-list">
              <button
                v-for="row in primaryRows"
                :key="row.id"
                class="info-row"
                type="button"
                @click="goPrimaryDetail(row)"
              >
                <div>
                  <p class="row-title">{{ getPrimaryTitle(row) }}</p>
                  <p class="row-meta">{{ getPrimaryMeta(row) }}</p>
                </div>
                <n-tag :type="getPrimaryTagType(row)" size="small" round>
                  {{ getPrimaryTagText(row) }}
                </n-tag>
              </button>
            </div>
            <n-empty v-else description="暂无待处理内容" />
          </n-card>

          <n-card class="dashboard-card" :bordered="false">
            <template #header>
              <div class="card-title">
                <TheIcon icon="material-symbols:bolt-outline-rounded" :size="20" />
                快捷入口
              </div>
            </template>
            <div class="quick-grid">
              <n-button
                v-for="entry in quickEntries"
                :key="entry.path"
                class="quick-button"
                secondary
                @click="goPage(entry.path)"
              >
                <template #icon>
                  <TheIcon :icon="entry.icon" :size="18" />
                </template>
                {{ entry.label }}
              </n-button>
            </div>
          </n-card>
        </div>

        <n-card class="dashboard-card" :bordered="false">
          <template #header>
            <div class="card-title">
              <TheIcon :icon="secondaryListIcon" :size="20" />
              {{ secondaryListTitle }}
            </div>
          </template>
          <div v-if="secondaryRows.length" class="compact-grid">
            <button
              v-for="row in secondaryRows"
              :key="row.id"
              class="compact-row"
              type="button"
              @click="goSecondaryDetail(row)"
            >
              <div>
                <p class="row-title">{{ getSecondaryTitle(row) }}</p>
                <p class="row-meta">{{ getSecondaryMeta(row) }}</p>
              </div>
              <TheIcon icon="material-symbols:chevron-right-rounded" :size="20" />
            </button>
          </div>
          <n-empty v-else description="暂无最近记录" />
        </n-card>
      </div>
    </n-spin>
  </AppPage>
</template>

<script setup>
import TheIcon from '@/components/icon/TheIcon.vue'
import examApi from '@/api/exam'
import { useAppStore, useUserStore } from '@/store'

const router = useRouter()
const appStore = useAppStore()
const userStore = useUserStore()
const loading = ref(false)
const dashboard = ref({
  role: 'user',
  stats: {},
  pending_gradings: [],
  recent_papers: [],
  available_papers: [],
  recent_attempts: [],
  recent_practices: [],
})

const paperStatusMap = {
  draft: '草稿',
  published: '已发布',
  closed: '已关闭',
}

const attemptStatusMap = {
  in_progress: '答题中',
  pending_review: '待阅卷',
  graded: '已完成',
  submitted: '已提交',
}

const isAdmin = computed(() => dashboard.value.role === 'admin')

const roleTitle = computed(() => (isAdmin.value ? '管理员工作台' : '我的学习工作台'))

const roleSubtitle = computed(() =>
  isAdmin.value ? '这里是题库、试卷和阅卷的处理入口' : '这里是考试、练习和成绩的个人入口'
)

const statCards = computed(() => {
  const stats = dashboard.value.stats || {}
  if (isAdmin.value) {
    return [
      {
        key: 'bank_count',
        label: '题库数量',
        value: stats.bank_count || 0,
        icon: 'material-symbols:library-books-outline',
        tone: 'blue',
      },
      {
        key: 'question_count',
        label: '题目数量',
        value: stats.question_count || 0,
        icon: 'material-symbols:checklist-rtl-rounded',
        tone: 'green',
      },
      {
        key: 'published_paper_count',
        label: '已发布试卷',
        value: stats.published_paper_count || 0,
        icon: 'material-symbols:description-outline-rounded',
        tone: 'amber',
      },
      {
        key: 'pending_grading_count',
        label: '待阅卷',
        value: stats.pending_grading_count || 0,
        icon: 'mdi-account-box',
        tone: 'rose',
      },
    ]
  }

  return [
    {
      key: 'available_paper_count',
      label: '可参加考试',
      value: stats.available_paper_count || 0,
      icon: 'material-symbols:edit-document',
      tone: 'blue',
    },
    {
      key: 'in_progress_attempt_count',
      label: '答题中',
      value: stats.in_progress_attempt_count || 0,
      icon: 'material-symbols:pending-actions-rounded',
      tone: 'amber',
    },
    {
      key: 'pending_review_count',
      label: '等待阅卷',
      value: stats.pending_review_count || 0,
      icon: 'material-symbols:grading-outline-rounded',
      tone: 'rose',
    },
    {
      key: 'practice_accuracy',
      label: '练习正确率',
      value: `${stats.practice_accuracy || 0}%`,
      icon: 'material-symbols:target',
      tone: 'violet',
    },
  ]
})

const quickEntries = computed(() => {
  if (isAdmin.value) {
    return [
      { label: '题库管理', path: '/exam/bank', icon: 'material-symbols:library-books-outline' },
      { label: '题目管理', path: '/exam/question', icon: 'material-symbols:checklist-rtl-rounded' },
      {
        label: '试卷管理',
        path: '/exam/paper',
        icon: 'material-symbols:description-outline-rounded',
      },
      {
        label: '阅卷中心',
        path: '/exam/grading',
        icon: 'material-symbols:grading-outline-rounded',
      },
    ]
  }
  return [
    { label: '我的答题', path: '/exam/answer', icon: 'material-symbols:edit-document' },
    { label: '练习中心', path: '/exam/practice', icon: 'material-symbols:school-outline-rounded' },
    { label: '知识文章', path: '/knowledge/published', icon: 'material-symbols:menu-book-outline' },
  ]
})

const primaryRows = computed(() =>
  isAdmin.value ? dashboard.value.pending_gradings || [] : dashboard.value.available_papers || []
)

const secondaryRows = computed(() =>
  isAdmin.value ? dashboard.value.recent_papers || [] : dashboard.value.recent_attempts || []
)

const primaryListTitle = computed(() => (isAdmin.value ? '待阅卷任务' : '可参加考试'))
const primaryListIcon = computed(() =>
  isAdmin.value ? 'material-symbols:grading-outline-rounded' : 'material-symbols:edit-document'
)
const secondaryListTitle = computed(() => (isAdmin.value ? '最近试卷' : '最近答题记录'))
const secondaryListIcon = computed(() =>
  isAdmin.value
    ? 'material-symbols:description-outline-rounded'
    : 'material-symbols:history-rounded'
)

onMounted(() => {
  loadDashboard()
})

async function loadDashboard() {
  loading.value = true
  try {
    const { data } = await examApi.getExamDashboard()
    dashboard.value = {
      ...dashboard.value,
      ...data,
    }
  } finally {
    loading.value = false
  }
}

function goPage(path) {
  router.push(path)
}

function goPrimaryDetail() {
  router.push(isAdmin.value ? '/exam/grading' : '/exam/answer')
}

function goSecondaryDetail() {
  router.push(isAdmin.value ? '/exam/paper' : '/exam/answer')
}

function getPrimaryTitle(row) {
  if (isAdmin.value) return row.paper?.title || '未命名试卷'
  return row.title || '未命名试卷'
}

function getPrimaryMeta(row) {
  if (isAdmin.value) {
    return `${row.user?.username || '未知用户'} · 提交于 ${row.submitted_at || '-'}`
  }
  return `${row.question_count || 0} 题 · 总分 ${row.total_score || 0} · ${
    row.duration_minutes || 0
  } 分钟`
}

function getPrimaryTagText(row) {
  if (isAdmin.value) return row.claimed_by_name || '未领取'
  if (!row.attempt) return '未开始'
  return attemptStatusMap[row.attempt.status] || row.attempt.status
}

function getPrimaryTagType(row) {
  if (isAdmin.value) return row.claimed_by ? 'warning' : 'error'
  if (!row.attempt) return 'info'
  return getAttemptStatusType(row.attempt.status)
}

function getSecondaryTitle(row) {
  if (isAdmin.value) return row.title || '未命名试卷'
  return row.paper?.title || '未命名试卷'
}

function getSecondaryMeta(row) {
  if (isAdmin.value) {
    return `${paperStatusMap[row.status] || row.status} · ${row.question_count || 0} 题 · 更新于 ${
      row.updated_at || '-'
    }`
  }
  return `${attemptStatusMap[row.status] || row.status} · 得分 ${row.total_score || 0} · ${
    row.submitted_at || row.started_at || '-'
  }`
}

function getAttemptStatusType(status) {
  if (status === 'graded') return 'success'
  if (status === 'pending_review') return 'warning'
  return 'info'
}
</script>

<style scoped>
.workbench-page {
  --workbench-card-bg: #fff;
  --workbench-card-border: transparent;
  --workbench-card-shadow: 0 6px 18px rgb(20 24 40 / 6%);
  --workbench-text: #1f2937;
  --workbench-strong: #111827;
  --workbench-muted: #6b7280;
  --workbench-row-bg: #fff;
  --workbench-row-border: #edf0f5;
  --workbench-hover-border: var(--primary-color);
  --workbench-hover-shadow: 0 6px 16px rgb(47 128 237 / 10%);
  --workbench-blue-bg: #e0f2fe;
  --workbench-blue-text: #0369a1;
  --workbench-green-bg: #dcfce7;
  --workbench-green-text: #15803d;
  --workbench-amber-bg: #fef3c7;
  --workbench-amber-text: #b45309;
  --workbench-rose-bg: #ffe4e6;
  --workbench-rose-text: #be123c;
  --workbench-violet-bg: #ede9fe;
  --workbench-violet-text: #6d28d9;

  display: flex;
  flex-direction: column;
  gap: 16px;
  color: var(--workbench-text);
}

.workbench-page.is-dark {
  --workbench-card-bg: #000;
  --workbench-card-border: #2a2b30;
  --workbench-card-shadow: none;
  --workbench-text: rgba(255, 255, 255, 0.88);
  --workbench-strong: rgba(255, 255, 255, 0.92);
  --workbench-muted: rgba(255, 255, 255, 0.62);
  --workbench-row-bg: #18191d;
  --workbench-row-border: #2a2b30;
  --workbench-hover-border: #60a5fa;
  --workbench-hover-shadow: 0 8px 18px rgb(0 0 0 / 28%);
  --workbench-blue-bg: rgba(59, 130, 246, 0.18);
  --workbench-blue-text: #93c5fd;
  --workbench-green-bg: rgba(34, 197, 94, 0.16);
  --workbench-green-text: #86efac;
  --workbench-amber-bg: rgba(245, 158, 11, 0.16);
  --workbench-amber-text: #fcd34d;
  --workbench-rose-bg: rgba(244, 63, 94, 0.16);
  --workbench-rose-text: #fda4af;
  --workbench-violet-bg: rgba(139, 92, 246, 0.18);
  --workbench-violet-text: #c4b5fd;
}

.dashboard-card {
  border: 1px solid var(--workbench-card-border);
  border-radius: 8px;
  background: var(--workbench-card-bg);
  box-shadow: var(--workbench-card-shadow);
}

.hero-main,
.hero-user,
.card-title,
.stat-card,
.info-row,
.compact-row {
  display: flex;
  align-items: center;
}

.hero-main {
  justify-content: space-between;
  gap: 16px;
}

.hero-user {
  min-width: 0;
  gap: 14px;
}

.hero-avatar {
  width: 60px;
  height: 60px;
  flex: 0 0 auto;
  border-radius: 50%;
  object-fit: cover;
}

.hero-title {
  margin: 0;
  color: var(--workbench-text);
  font-size: 22px;
  font-weight: 700;
}

.hero-subtitle,
.stat-label,
.row-meta {
  margin: 0;
  color: var(--workbench-muted);
}

.hero-subtitle {
  margin-top: 6px;
  font-size: 14px;
}

.stat-grid {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 16px;
}

.stat-card {
  min-height: 116px;
  gap: 14px;
}

.stat-icon {
  display: flex;
  width: 48px;
  height: 48px;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
}

.stat-value {
  margin: 0;
  color: var(--workbench-strong);
  font-size: 28px;
  font-weight: 700;
  line-height: 1.2;
}

.stat-label {
  margin-top: 4px;
  font-size: 13px;
}

.blue .stat-icon {
  background: var(--workbench-blue-bg);
  color: var(--workbench-blue-text);
}

.green .stat-icon {
  background: var(--workbench-green-bg);
  color: var(--workbench-green-text);
}

.amber .stat-icon {
  background: var(--workbench-amber-bg);
  color: var(--workbench-amber-text);
}

.rose .stat-icon {
  background: var(--workbench-rose-bg);
  color: var(--workbench-rose-text);
}

.violet .stat-icon {
  background: var(--workbench-violet-bg);
  color: var(--workbench-violet-text);
}

.content-grid {
  display: grid;
  grid-template-columns: minmax(0, 2fr) minmax(280px, 1fr);
  gap: 16px;
}

.card-title {
  gap: 8px;
  color: var(--workbench-text);
  font-size: 16px;
  font-weight: 700;
}

.row-list,
.compact-grid,
.quick-grid {
  display: grid;
  gap: 10px;
}

.info-row,
.compact-row {
  width: 100%;
  min-height: 64px;
  justify-content: space-between;
  gap: 12px;
  border: 1px solid var(--workbench-row-border);
  border-radius: 8px;
  background: var(--workbench-row-bg);
  color: var(--workbench-text);
  padding: 12px;
  text-align: left;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.info-row:hover,
.compact-row:hover {
  border-color: var(--workbench-hover-border);
  box-shadow: var(--workbench-hover-shadow);
}

.row-title {
  margin: 0;
  overflow: hidden;
  color: var(--workbench-text);
  font-size: 14px;
  font-weight: 600;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.row-meta {
  margin-top: 6px;
  font-size: 12px;
}

.quick-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

.quick-button {
  justify-content: flex-start;
}

.compact-grid {
  grid-template-columns: repeat(2, minmax(0, 1fr));
}

@media (max-width: 1100px) {
  .stat-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .content-grid,
  .compact-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .hero-main {
    align-items: flex-start;
    flex-direction: column;
  }

  .stat-grid,
  .quick-grid {
    grid-template-columns: 1fr;
  }

  .hero-title {
    font-size: 20px;
  }
}
</style>
