<template>
  <n-breadcrumb class="app-breadcrumb">
    <n-breadcrumb-item v-for="(item, index) in breadcrumbItems" :key="item.path">
      <span
        class="app-breadcrumb-item"
        :class="{ 'is-current': index === breadcrumbItems.length - 1 }"
        @click="handleBreadClick(item, index)"
      >
        {{ item.meta.title }}
      </span>
    </n-breadcrumb-item>
  </n-breadcrumb>
</template>

<script setup>
const router = useRouter()
const route = useRoute()

const breadcrumbItems = computed(() => route.matched.filter((item) => !!item.meta?.title))

function handleBreadClick(item, index) {
  if (index === breadcrumbItems.value.length - 1) return
  const path = item.path
  if (path === route.path) return
  router.push(path)
}
</script>

<style scoped>
.app-breadcrumb {
  line-height: 1;
}

.app-breadcrumb-item {
  cursor: pointer;
}

.app-breadcrumb-item.is-current {
  cursor: default;
}
</style>
