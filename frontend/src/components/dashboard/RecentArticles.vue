<template>
  <div class="recent-articles card-static">
    <h3 class="section-title">最近高相关文章</h3>
    <el-scrollbar max-height="280px">
      <div v-if="!articles || articles.length === 0" class="empty-state">
        暂无文章
      </div>
      <div v-else class="article-list">
        <a
          v-for="article in articles"
          :key="article.id"
          :href="`/articles/${article.id}`"
          target="_blank"
          class="article-item"
        >
          <img v-if="article.images && article.images.length > 0" :src="article.images[0]" class="article-thumb">
          <div class="article-info">
            <p class="article-title">{{ article.title }}</p>
            <p class="article-meta">
              <span>公众号 {{ article.account_name || article.account_id }}</span>
              <span>{{ formatDate(article.published_at) }}</span>
            </p>
          </div>
          <el-tag v-if="article.ai_relevance_ratio && article.ai_relevance_ratio > 0.5" type="warning" size="small">
            AI {{ Math.round(article.ai_relevance_ratio * 100) }}%
          </el-tag>
        </a>
      </div>
    </el-scrollbar>
  </div>
</template>

<script setup>
defineProps({
  articles: {
    type: Array,
    default: () => []
  }
})

function formatDate(date) {
  if (!date) return '-'
  return new Date(date).toLocaleDateString('zh-CN')
}
</script>

<style lang="scss" scoped>
.recent-articles {
  padding: 20px;
}

.section-title {
  font-size: 16px;
  font-weight: 600;
  margin-bottom: 16px;
}

.empty-state {
  text-align: center;
  color: $color-text-secondary;
  padding: 40px 0;
}

.article-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.article-item {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 12px;
  border-radius: $radius-sm;
  text-decoration: none;
  color: inherit;
  transition: background-color $transition-fast;

  &:hover {
    background-color: rgba($color-primary, 0.05);
  }
}

.article-thumb {
  width: 48px;
  height: 48px;
  border-radius: $radius-sm;
  object-fit: cover;
}

.article-info {
  flex: 1;
  min-width: 0;
}

.article-title {
  font-size: 14px;
  font-weight: 500;
  color: $color-text;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.article-meta {
  display: flex;
  gap: 12px;
  font-size: 12px;
  color: $color-text-secondary;
  margin-top: 4px;
}
</style>
