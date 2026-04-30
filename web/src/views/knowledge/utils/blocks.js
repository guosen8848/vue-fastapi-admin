const BLOCK_TYPE_LABELS = {
  text: '文本',
  md: 'Markdown',
  docx: 'Word',
  pdf: 'PDF',
  xlsx: 'Excel',
}

function createClientKey() {
  if (globalThis.crypto?.randomUUID) {
    return globalThis.crypto.randomUUID()
  }
  return `local-${Date.now()}-${Math.random().toString(16).slice(2)}`
}

export function getBlockLabel(blockType) {
  return BLOCK_TYPE_LABELS[blockType] || blockType || '内容块'
}

export function attachBlockKey(block = {}) {
  return {
    ...block,
    client_key: block.client_key || block.id || block.temp_token || createClientKey(),
  }
}

export function normalizeBlocks(blocks = []) {
  return blocks.map((block) => attachBlockKey(block))
}

export function createTextBlock() {
  return attachBlockKey({
    block_type: 'text',
    text_content: '',
  })
}

export function stripBlockClientFields(blocks = []) {
  return blocks.map((block) => {
    const nextBlock = { ...block }
    delete nextBlock.client_key
    return nextBlock
  })
}

export function formatFileSize(size) {
  if (!size) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB']
  let value = size
  let unitIndex = 0
  while (value >= 1024 && unitIndex < units.length - 1) {
    value /= 1024
    unitIndex += 1
  }
  return `${value >= 10 || unitIndex === 0 ? value.toFixed(0) : value.toFixed(1)} ${
    units[unitIndex]
  }`
}
