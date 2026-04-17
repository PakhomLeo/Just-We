<template>
  <div class="article-detail">
    <el-button @click="router.back()">返回列表</el-button>

    <el-skeleton v-if="loading" :rows="8" animated class="article-skeleton" />

    <template v-else-if="article">
      <div class="hero card-static">
        <img v-if="article.cover_image" :src="article.cover_image" class="hero-cover">
        <div class="hero-copy">
          <h1>{{ article.title }}</h1>
          <div class="meta-grid">
            <span>作者：{{ article.author || '-' }}</span>
            <span>发布时间：{{ formatDateTime(article.published_at) }}</span>
            <span>抓取通道：{{ article.fetch_mode || '-' }}</span>
            <span>监测对象 ID：{{ article.monitored_account_id || '-' }}</span>
          </div>
          <div class="hero-actions">
            <el-tag :type="aiTagType(article.ai_relevance_ratio)">
              AI 相关度 {{ article.ai_relevance_ratio !== null && article.ai_relevance_ratio !== undefined ? `${Math.round(article.ai_relevance_ratio * 100)}%` : '-' }}
            </el-tag>
            <el-link :href="article.url" target="_blank" type="primary">打开原文</el-link>
          </div>
        </div>
      </div>

      <div class="detail-grid">
        <section class="content-card card-static">
          <h3>正文内容</h3>
          <div class="article-content" v-html="article.raw_content || article.content" />
        </section>

        <aside class="sidebar">
          <div class="sidebar-card card-static">
            <h3>AI 判定</h3>
            <p class="sidebar-text">{{ article.ai_judgment?.reason || '暂无 AI 理由' }}</p>
            <div class="keywords">
              <el-tag v-for="keyword in article.ai_judgment?.keywords || []" :key="keyword" effect="plain">
                {{ keyword }}
              </el-tag>
            </div>
          </div>

          <div class="sidebar-card card-static">
            <h3>本地化图片</h3>
            <div v-if="article.images?.length" class="image-grid">
              <el-image
                v-for="image in article.images"
                :key="image"
                :src="image"
                :preview-src-list="article.images"
                fit="cover"
                class="detail-image"
              />
            </div>
            <el-empty v-else description="无图片" :image-size="80" />
          </div>

          <div class="sidebar-card card-static">
            <h3>原始载荷</h3>
            <pre class="payload-viewer">{{ JSON.stringify(article.source_payload || {}, null, 2) }}</pre>
          </div>
        </aside>
      </div>
    </template>

    <el-empty v-else description="文章不存在" />
  </div>
</template>

<script setup>
import { onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { getArticle } from '@/api/articles'

const route = useRoute()
const router = useRouter()
const article = ref(null)
const loading = ref(false)

onMounted(loadArticle)

async function loadArticle() {
  loading.value = true
  try {
    const response = await getArticle(route.params.id)
    article.value = response.data
  } finally {
    loading.value = false
  }
}

function formatDateTime(value) {
  if (!value) return '-'
  return new Date(value).toLocaleString('zh-CN')
}

function aiTagType(value) {
  if (value >= 0.8) return 'success'
  if (value >= 0.5) return 'warning'
  return 'info'
}
</script>

<style lang="scss" scoped>
.article-detail {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.article-skeleton {
  padding: 24px;
  background: $color-card;
  border-radius: 16px;
}

.hero {
  padding: 24px;
  display: grid;
  grid-template-columns: 200px 1fr;
  gap: 24px;
}

.hero-cover {
  width: 100%;
  height: 200px;
  object-fit: cover;
  border-radius: 16px;
}

.hero-copy {
  display: flex;
  flex-direction: column;
  gap: 16px;

  h1 {
    margin: 0;
    line-height: 1.4;
  }
}

.meta-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
  color: $color-text-secondary;
}

.hero-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
  align-items: center;
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1fr) 320px;
  gap: 24px;
}

.content-card,
.sidebar-card {
  padding: 24px;
}

.content-card h3,
.sidebar-card h3 {
  margin-top: 0;
}

.article-content {
  line-height: 1.8;

  :deep(img) {
    max-width: 100%;
    border-radius: 12px;
  }
}

.sidebar {
  display: flex;
  flex-direction: column;
  gap: 20px;
}

.sidebar-text {
  margin: 0;
  color: $color-text-secondary;
}

.keywords {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
  margin-top: 12px;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 12px;
}

.detail-image {
  width: 100%;
  aspect-ratio: 1;
  border-radius: 12px;
}

.payload-viewer {
  margin: 0;
  padding: 16px;
  border-radius: 12px;
  background: $color-bg;
  max-height: 320px;
  overflow: auto;
  font-size: 12px;
  white-space: pre-wrap;
  word-break: break-word;
}

@media (max-width: 960px) {
  .hero,
  .detail-grid,
  .meta-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 768px) {
  .hero,
  .content-card,
  .sidebar-card {
    padding: 16px;
  }

  .hero-cover {
    height: 180px;
  }
}
</style>
