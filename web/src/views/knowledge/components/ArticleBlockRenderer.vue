<script setup>
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { NButton, NEmpty, NSpin, NTag } from 'naive-ui'

import knowledgeApi from '@/api/knowledge'
import { useAppStore } from '@/store'

import { formatFileSize, getBlockLabel } from '../utils/blocks'

const props = defineProps({
  blocks: {
    type: Array,
    default: () => [],
  },
  previewScope: {
    type: String,
    default: 'article',
  },
})

const appStore = useAppStore()
const pdfPreviewUrls = ref({})
const pdfLoadingKeys = ref({})
const pdfFailedKeys = ref({})
const downloadLoadingKeys = ref({})
let previewVersion = 0

const normalizedBlocks = computed(() =>
  (props.blocks || []).map((block, index) => ({
    ...block,
    __key: block.client_key || block.id || block.temp_token || `${block.block_type}-${index}`,
  }))
)

const pdfPreviewSignature = computed(() =>
  normalizedBlocks.value
    .filter((block) => block.block_type === 'pdf')
    .map(
      (block) => `${props.previewScope}:${block.__key}:${block.id || ''}:${block.temp_token || ''}`
    )
    .join('|')
)

watch(
  pdfPreviewSignature,
  async () => {
    previewVersion += 1
    const currentVersion = previewVersion
    clearPdfPreviewUrls()

    const pdfBlocks = normalizedBlocks.value.filter((block) => block.block_type === 'pdf')
    if (!pdfBlocks.length) return

    await Promise.all(
      pdfBlocks.map(async (block) => {
        pdfLoadingKeys.value[block.__key] = true
        pdfFailedKeys.value[block.__key] = false
        try {
          const requestApi =
            props.previewScope === 'published' && !block.temp_token
              ? knowledgeApi.getPublishedKnowledgeArticleBlockFile
              : knowledgeApi.getKnowledgeArticleBlockFile
          const { data } = await requestApi(
            block.temp_token ? { temp_token: block.temp_token } : { block_id: block.id }
          )
          if (currentVersion !== previewVersion) return
          pdfPreviewUrls.value[block.__key] = URL.createObjectURL(data)
        } catch (error) {
          if (currentVersion !== previewVersion) return
          pdfFailedKeys.value[block.__key] = true
        } finally {
          if (currentVersion === previewVersion) {
            pdfLoadingKeys.value[block.__key] = false
          }
        }
      })
    )
  },
  { immediate: true }
)

onBeforeUnmount(() => {
  clearPdfPreviewUrls()
})

function clearPdfPreviewUrls() {
  Object.values(pdfPreviewUrls.value).forEach((url) => {
    if (url) {
      URL.revokeObjectURL(url)
    }
  })
  pdfPreviewUrls.value = {}
  pdfLoadingKeys.value = {}
  pdfFailedKeys.value = {}
}

function getSheetColumnCount(sheet) {
  if (sheet?.max_column_count) {
    return sheet.max_column_count
  }
  return Math.max(...(sheet?.rows || []).map((row) => row.length), 0)
}

function getBlockRequestApi(block) {
  if (props.previewScope === 'published' && !block.temp_token) {
    return knowledgeApi.getPublishedKnowledgeArticleBlockFile
  }
  return knowledgeApi.getKnowledgeArticleBlockFile
}

function isDownloadableBlock(block) {
  return block.block_type !== 'text' && Boolean(block.id || block.temp_token)
}

async function handleDownloadBlock(block) {
  if (!isDownloadableBlock(block)) return

  downloadLoadingKeys.value[block.__key] = true
  try {
    const { data } = await getBlockRequestApi(block)(
      block.temp_token ? { temp_token: block.temp_token } : { block_id: block.id }
    )
    const downloadUrl = URL.createObjectURL(data)
    const link = document.createElement('a')
    link.href = downloadUrl
    link.download = block.file_name || 'knowledge-attachment'
    document.body.appendChild(link)
    link.click()
    link.remove()
    window.setTimeout(() => {
      URL.revokeObjectURL(downloadUrl)
    }, 1000)
  } finally {
    downloadLoadingKeys.value[block.__key] = false
  }
}
</script>

<template>
  <div class="article-blocks" :class="{ 'is-dark': appStore.isDark }">
    <section v-for="block in normalizedBlocks" :key="block.__key" class="article-block-card">
      <header class="article-block-card-header">
        <div class="article-block-card-meta">
          <NTag size="small" type="info" :bordered="false">
            {{ getBlockLabel(block.block_type) }}
          </NTag>
          <span v-if="block.file_name" class="article-block-file-name">{{ block.file_name }}</span>
        </div>
        <div class="article-block-card-actions">
          <span v-if="block.file_size" class="article-block-file-size">{{
            formatFileSize(block.file_size)
          }}</span>
          <NButton
            v-if="isDownloadableBlock(block)"
            size="small"
            quaternary
            type="primary"
            :loading="Boolean(downloadLoadingKeys[block.__key])"
            @click="handleDownloadBlock(block)"
          >
            下载附件
          </NButton>
        </div>
      </header>

      <div v-if="block.block_type === 'text'" class="article-block-text">
        {{ block.text_content }}
      </div>

      <div
        v-else-if="block.block_type === 'md' || block.block_type === 'docx'"
        class="article-block-rich"
        v-html="block.render_html || '<p>暂无可展示内容</p>'"
      />

      <div v-else-if="block.block_type === 'pdf'" class="article-block-pdf">
        <NSpin :show="Boolean(pdfLoadingKeys[block.__key])">
          <iframe
            v-if="pdfPreviewUrls[block.__key]"
            :src="pdfPreviewUrls[block.__key]"
            class="article-block-pdf-frame"
            title="PDF 预览"
          />
          <NEmpty v-else-if="pdfFailedKeys[block.__key]" description="PDF 预览加载失败" />
        </NSpin>
      </div>

      <div v-else-if="block.block_type === 'xlsx'" class="article-block-sheet-list">
        <section
          v-for="sheet in block.render_json?.sheets || []"
          :key="`${block.__key}-${sheet.name}`"
          class="article-block-sheet"
        >
          <header class="article-block-sheet-header">
            <h4>{{ sheet.name }}</h4>
            <span v-if="sheet.truncated"
              >仅展示前 {{ block.render_json?.preview_row_limit || 200 }} 行</span
            >
          </header>
          <div class="article-block-sheet-table-wrap">
            <table class="article-block-sheet-table">
              <tbody>
                <tr v-for="(row, rowIndex) in sheet.rows" :key="`${sheet.name}-${rowIndex}`">
                  <td
                    v-for="columnIndex in getSheetColumnCount(sheet)"
                    :key="`${sheet.name}-${rowIndex}-${columnIndex}`"
                  >
                    {{ row[columnIndex - 1] ?? '' }}
                  </td>
                </tr>
              </tbody>
            </table>
            <NEmpty v-if="!sheet.rows?.length" description="当前工作表暂无内容" />
          </div>
        </section>
      </div>
    </section>
  </div>
</template>

<style scoped lang="scss">
.article-blocks {
  --article-block-card-bg: #fff;
  --article-block-fill: #f8fafc;
  --article-block-border: #eef2f7;
  --article-block-grid-border: #e2e8f0;
  --article-block-text: #1f2937;
  --article-block-title: #111827;
  --article-block-muted: #94a3b8;
  --article-block-sheet-title: #1e293b;
  --article-block-sheet-text: #334155;

  display: flex;
  flex-direction: column;
  gap: 16px;
}

.article-blocks.is-dark {
  --article-block-card-bg: #000;
  --article-block-fill: #18191d;
  --article-block-border: #2a2b30;
  --article-block-grid-border: #2a2b30;
  --article-block-text: rgba(255, 255, 255, 0.88);
  --article-block-title: rgba(255, 255, 255, 0.92);
  --article-block-muted: rgba(255, 255, 255, 0.56);
  --article-block-sheet-title: rgba(255, 255, 255, 0.88);
  --article-block-sheet-text: rgba(255, 255, 255, 0.82);
}

.article-block-card {
  padding: 18px 20px;
  border: 1px solid var(--article-block-border);
  border-radius: 8px;
  background: var(--article-block-card-bg);
}

.article-block-card-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.article-block-card-actions {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.article-block-card-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.article-block-file-name {
  min-width: 0;
  font-size: 14px;
  font-weight: 600;
  color: var(--article-block-text);
  word-break: break-word;
}

.article-block-file-size {
  font-size: 12px;
  color: var(--article-block-muted);
  white-space: nowrap;
}

.article-block-text {
  font-size: 15px;
  line-height: 1.9;
  color: var(--article-block-text);
  white-space: pre-wrap;
  word-break: break-word;
}

.article-block-rich {
  font-size: 15px;
  line-height: 1.8;
  color: var(--article-block-text);
  word-break: break-word;
}

.article-block-rich :deep(h1),
.article-block-rich :deep(h2),
.article-block-rich :deep(h3),
.article-block-rich :deep(h4) {
  margin: 1.2em 0 0.6em;
  font-weight: 700;
  color: var(--article-block-title);
}

.article-block-rich :deep(p),
.article-block-rich :deep(li) {
  line-height: 1.85;
}

.article-block-rich :deep(pre) {
  padding: 14px 16px;
  border-radius: 12px;
  overflow: auto;
  background: #0f172a;
  color: #e2e8f0;
}

.article-block-rich :deep(code) {
  font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace;
}

.article-block-rich :deep(table) {
  width: 100%;
  border-collapse: collapse;
}

@media (max-width: 640px) {
  .article-block-card-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .article-block-card-actions {
    width: 100%;
    justify-content: flex-start;
  }
}

.article-block-rich :deep(th),
.article-block-rich :deep(td) {
  padding: 10px 12px;
  border: 1px solid var(--article-block-grid-border);
}

.article-block-pdf-frame {
  width: 100%;
  height: 640px;
  border: 1px solid var(--article-block-grid-border);
  border-radius: 8px;
  background: var(--article-block-card-bg);
}

.article-block-sheet-list {
  display: flex;
  flex-direction: column;
  gap: 18px;
}

.article-block-sheet-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 10px;

  h4 {
    margin: 0;
    font-size: 14px;
    font-weight: 700;
    color: var(--article-block-sheet-title);
  }

  span {
    font-size: 12px;
    color: var(--article-block-muted);
  }
}

.article-block-sheet-table-wrap {
  overflow: auto;
  border: 1px solid var(--article-block-grid-border);
  border-radius: 8px;
}

.article-block-sheet-table {
  min-width: 100%;
  border-collapse: collapse;
  background: var(--article-block-card-bg);

  td {
    min-width: 120px;
    padding: 10px 12px;
    border-right: 1px solid var(--article-block-grid-border);
    border-bottom: 1px solid var(--article-block-grid-border);
    font-size: 13px;
    line-height: 1.6;
    color: var(--article-block-sheet-text);
    white-space: pre-wrap;
    word-break: break-word;
  }

  tr:last-child td {
    border-bottom: none;
  }

  td:last-child {
    border-right: none;
  }
}

@media (max-width: 960px) {
  .article-block-card {
    padding: 16px;
  }

  .article-block-card-header {
    align-items: flex-start;
    flex-direction: column;
  }

  .article-block-pdf-frame {
    height: 420px;
  }
}
</style>
