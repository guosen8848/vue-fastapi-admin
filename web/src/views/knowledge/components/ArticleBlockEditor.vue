<script setup>
import { computed, ref } from 'vue'
import { NButton, NEmpty, NInput, NTag } from 'naive-ui'

import knowledgeApi from '@/api/knowledge'
import { useAppStore } from '@/store'

import ArticleBlockRenderer from './ArticleBlockRenderer.vue'
import { attachBlockKey, getBlockLabel } from '../utils/blocks'

const props = defineProps({
  modelValue: {
    type: Array,
    default: () => [],
  },
})

const emit = defineEmits(['update:modelValue'])

const appStore = useAppStore()
const fileInputRef = ref(null)
const uploading = ref(false)

const blocks = computed({
  get: () => props.modelValue || [],
  set: (value) => emit('update:modelValue', value),
})

function updateBlocks(nextBlocks) {
  blocks.value = nextBlocks
}

function handleTriggerUpload() {
  fileInputRef.value?.click()
}

async function handleSelectFiles(event) {
  const files = Array.from(event.target?.files || [])
  if (!files.length) return

  uploading.value = true
  try {
    const uploadedBlocks = []
    for (const file of files) {
      const { data } = await knowledgeApi.uploadKnowledgeArticleBlock(file)
      uploadedBlocks.push(attachBlockKey(data))
    }
    updateBlocks([...blocks.value, ...uploadedBlocks])
    $message.success(`已添加 ${uploadedBlocks.length} 个文件内容块`)
  } finally {
    uploading.value = false
    if (event.target) {
      event.target.value = ''
    }
  }
}

function handleMoveBlock(index, direction) {
  const nextBlocks = [...blocks.value]
  const targetIndex = direction === 'up' ? index - 1 : index + 1
  if (targetIndex < 0 || targetIndex >= nextBlocks.length) return
  ;[nextBlocks[index], nextBlocks[targetIndex]] = [nextBlocks[targetIndex], nextBlocks[index]]
  updateBlocks(nextBlocks)
}

function handleRemoveBlock(index) {
  const nextBlocks = [...blocks.value]
  nextBlocks.splice(index, 1)
  updateBlocks(nextBlocks)
}

function handleUpdateTextBlock(index, value) {
  const nextBlocks = [...blocks.value]
  nextBlocks[index] = {
    ...nextBlocks[index],
    text_content: value,
  }
  updateBlocks(nextBlocks)
}
</script>

<template>
  <div class="article-block-editor" :class="{ 'is-dark': appStore.isDark }">
    <div class="article-block-editor-toolbar">
      <div class="article-block-editor-actions">
        <NButton type="primary" :loading="uploading" @click="handleTriggerUpload">上传文件</NButton>
        <input
          ref="fileInputRef"
          class="article-block-editor-input"
          type="file"
          accept=".md,.docx,.pdf,.xlsx"
          multiple
          @change="handleSelectFiles"
        />
      </div>
      <p>
        支持 `.md / .docx / .pdf / .xlsx`，文件只做展示，不在线编辑，可通过上下移动调整展示顺序。
      </p>
    </div>

    <NEmpty v-if="!blocks.length" description="请先上传文件" />

    <div v-else class="article-block-editor-list">
      <section
        v-for="(block, index) in blocks"
        :key="block.client_key"
        class="article-block-editor-card"
      >
        <header class="article-block-editor-card-header">
          <div class="article-block-editor-card-title">
            <h4>{{ getBlockLabel(block.block_type) }} {{ index + 1 }}</h4>
            <NTag v-if="block.file_name" size="small" type="info" :bordered="false">
              {{ block.file_name }}
            </NTag>
          </div>
          <div class="article-block-editor-card-actions">
            <NButton
              text
              type="primary"
              :disabled="index === 0"
              @click="handleMoveBlock(index, 'up')"
            >
              上移
            </NButton>
            <NButton
              text
              type="primary"
              :disabled="index === blocks.length - 1"
              @click="handleMoveBlock(index, 'down')"
            >
              下移
            </NButton>
            <NButton text type="error" @click="handleRemoveBlock(index)">删除</NButton>
          </div>
        </header>

        <NInput
          v-if="block.block_type === 'text'"
          :value="block.text_content"
          type="textarea"
          placeholder="请输入正文内容"
          :autosize="{ minRows: 6, maxRows: 12 }"
          @update:value="(value) => handleUpdateTextBlock(index, value)"
        />

        <ArticleBlockRenderer v-else :blocks="[block]" />
      </section>
    </div>
  </div>
</template>

<style scoped lang="scss">
.article-block-editor {
  --article-editor-card-bg: #fff;
  --article-editor-fill: #f8fafc;
  --article-editor-border: #e2e8f0;
  --article-editor-soft-border: #eef2f7;
  --article-editor-text: #111827;
  --article-editor-muted: #64748b;

  display: flex;
  flex-direction: column;
  gap: 16px;
}

.article-block-editor.is-dark {
  --article-editor-card-bg: #000;
  --article-editor-fill: #18191d;
  --article-editor-border: #2a2b30;
  --article-editor-soft-border: #2a2b30;
  --article-editor-text: rgba(255, 255, 255, 0.9);
  --article-editor-muted: rgba(255, 255, 255, 0.62);
}

.article-block-editor-toolbar {
  padding: 16px 18px;
  border: 1px solid var(--article-editor-soft-border);
  border-radius: 8px;
  background: var(--article-editor-fill);

  p {
    margin: 10px 0 0;
    font-size: 13px;
    line-height: 1.7;
    color: var(--article-editor-muted);
  }
}

.article-block-editor-actions {
  display: flex;
  align-items: center;
  gap: 12px;
  flex-wrap: wrap;
}

.article-block-editor-input {
  display: none;
}

.article-block-editor-list {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.article-block-editor-card {
  padding: 18px;
  border: 1px solid var(--article-editor-border);
  border-radius: 8px;
  background: var(--article-editor-card-bg);
}

.article-block-editor-card-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 14px;
  margin-bottom: 14px;
}

.article-block-editor-card-title {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;

  h4 {
    margin: 0;
    font-size: 15px;
    font-weight: 700;
    color: var(--article-editor-text);
  }
}

.article-block-editor-card-actions {
  display: flex;
  align-items: center;
  gap: 8px;
}

@media (max-width: 960px) {
  .article-block-editor-card-header {
    flex-direction: column;
  }

  .article-block-editor-card-actions {
    width: 100%;
    justify-content: flex-end;
    flex-wrap: wrap;
  }
}
</style>
