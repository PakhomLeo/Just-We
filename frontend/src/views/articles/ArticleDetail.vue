<template>
  <div class="article-detail">
    <el-button @click="goBack" class="back-btn">
      <el-icon><ArrowLeft /></el-icon>
      返回
    </el-button>

    <div v-if="article" class="detail-layout">
      <div class="article-main card-static">
        <h1 class="article-title">{{ article.title }}</h1>

        <div class="article-meta">
          <span class="account-name">{{ article.account_name }}</span>
          <span class="publish-time">{{ formatDateTime(article.publish_time) }}</span>
        </div>

        <div class="article-content" v-html="article.content" />
      </div>

      <div class="article-sidebar">
        <div class="sidebar-card card-static">
          <h4>AI 判断</h4>
          <el-tag :type="getAiTagType(article.ai_ratio)" size="large">
            {{ Math.round(article.ai_ratio * 100) }}% AI生成
          </el-tag>

          <div v-if="article.ai_reason" class="ai-reason">
            <h5>判断理由</h5>
            <p>{{ article.ai_reason }}</p>
          </div>
        </div>

        <div v-if="article.images?.length" class="sidebar-card card-static">
          <h4>图片列表</h4>
          <div class="image-grid">
            <el-image
              v-for="(img, index) in article.images"
              :key="index"
              :src="img"
              :preview-src-list="article.images"
              fit="cover"
              class="content-image"
            />
          </div>
        </div>
      </div>
    </div>

    <div v-else-if="loading" class="loading-state">
      <el-icon class="is-loading" :size="32"><Loading /></el-icon>
    </div>

    <div v-else class="not-found card-static">
      <p>文章不存在</p>
    </div>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ArrowLeft, Loading } from '@element-plus/icons-vue'
import { getArticle } from '@/api/articles'

const route = useRoute()
const router = useRouter()

const article = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const response = await getArticle(route.params.id)
    article.value = response.data
  } catch (error) {
    article.value = null
  } finally {
    loading.value = false
  }
})

function goBack() {
  router.back()
}

function formatDateTime(date) {
  return new Date(date).toLocaleString('zh-CN')
}

function getAiTagType(ratio) {
  if (ratio > 0.7) return 'danger'
  if (ratio > 0.4) return 'warning'
  return 'success'
}
</script>

<style lang="scss" scoped>
.article-detail {
  max-width: 1200px;
  margin: 0 auto;
}

.back-btn {
  margin-bottom: 20px;
}

.detail-layout {
  display: grid;
  grid-template-columns: 1fr 320px;
  gap: 24px;
}

.article-main {
  padding: 32px;
}

.article-title {
  font-size: 24px;
  font-weight: 700;
  line-height: 1.4;
  margin-bottom: 16px;
}

.article-meta {
  display: flex;
  gap: 16px;
  color: $color-text-secondary;
  font-size: 14px;
  margin-bottom: 24px;
  padding-bottom: 24px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.05);
}

.article-content {
  font-size: 16px;
  line-height: 1.8;
  color: $color-text;

  :deep(img) {
    max-width: 100%;
    border-radius: $radius-sm;
    margin: 16px 0;
  }

  :deep(p) {
    margin-bottom: 16px;
  }
}

.article-sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sidebar-card {
  padding: 20px;

  h4 {
    font-size: 14px;
    font-weight: 600;
    margin-bottom: 12px;
  }
}

.ai-reason {
  margin-top: 16px;

  h5 {
    font-size: 12px;
    color: $color-text-secondary;
    margin-bottom: 8px;
  }

  p {
    font-size: 14px;
    color: $color-text;
    line-height: 1.6;
  }
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 8px;
}

.content-image {
  width: 100%;
  aspect-ratio: 1;
  border-radius: $radius-sm;
  cursor: pointer;
}

.loading-state,
.not-found {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 400px;
  color: $color-text-secondary;
}
</style>
