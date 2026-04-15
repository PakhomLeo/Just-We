<template>
  <div class="article-list">
    <div class="toolbar">
      <el-input
        v-model="searchQuery"
        placeholder="搜索文章标题"
        :prefix-icon="Search"
        style="width: 240px"
        clearable
      />

      <div class="ai-ratio-filter">
        <span class="filter-label">AI 占比:</span>
        <el-slider
          v-model="aiRatioRange"
          range
          :min="0"
          :max="100"
          style="width: 200px"
        />
        <span class="ratio-value">{{ aiRatioRange[0] }}% - {{ aiRatioRange[1] }}%</span>
      </div>
    </div>

    <div class="table-container card-static">
      <el-table :data="filteredArticles" v-loading="loading" stripe>
        <el-table-column label="标题" min-width="200">
          <template #default="{ row }">
            <a
              :href="`/articles/${row.id}`"
              target="_blank"
              class="article-link"
              @click.prevent="openDetail(row.id)"
            >
              <img v-if="row.thumbnail" :src="row.thumbnail" class="article-thumb">
              <span class="article-title">{{ row.title }}</span>
            </a>
          </template>
        </el-table-column>

        <el-table-column prop="account_name" label="公众号" width="140" />

        <el-table-column prop="publish_time" label="发布时间" width="120">
          <template #default="{ row }">
            {{ formatDate(row.publish_time) }}
          </template>
        </el-table-column>

        <el-table-column prop="ai_ratio" label="AI 占比" width="100">
          <template #default="{ row }">
            <el-tag :type="getAiTagType(row.ai_ratio)" size="small">
              {{ Math.round(row.ai_ratio * 100) }}%
            </el-tag>
          </template>
        </el-table-column>

        <el-table-column prop="source" label="来源" width="100">
          <template #default="{ row }">
            {{ row.source || '-' }}
          </template>
        </el-table-column>

        <el-table-column label="操作" width="100" fixed="right">
          <template #default="{ row }">
            <el-button size="small" @click="openDetail(row.id)">
              查看
            </el-button>
          </template>
        </el-table-column>
      </el-table>

      <div class="pagination">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :total="total"
          :page-sizes="[10, 20, 50, 100]"
          layout="total, sizes, prev, pager, next"
          @size-change="handleSizeChange"
          @current-change="handleCurrentChange"
        />
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { Search } from '@element-plus/icons-vue'
import { getArticles } from '@/api/articles'

const router = useRouter()

const searchQuery = ref('')
const aiRatioRange = ref([0, 100])
const loading = ref(false)
const currentPage = ref(1)
const pageSize = ref(20)
const total = ref(0)
const articles = ref([])

const filteredArticles = computed(() => {
  return articles.value.filter(article => {
    if (searchQuery.value) {
      const query = searchQuery.value.toLowerCase()
      if (!article.title.toLowerCase().includes(query)) return false
    }
    const aiPercent = article.ai_ratio * 100
    if (aiPercent < aiRatioRange.value[0] || aiPercent > aiRatioRange.value[1]) {
      return false
    }
    return true
  })
})

onMounted(async () => {
  await fetchArticles()
})

async function fetchArticles() {
  loading.value = true
  try {
    const response = await getArticles({
      page: currentPage.value,
      page_size: pageSize.value
    })
    articles.value = response.data.items || response.data || []
    total.value = response.data.total || articles.value.length
  } finally {
    loading.value = false
  }
}

function openDetail(id) {
  router.push(`/articles/${id}`)
}

function handleSizeChange() {
  fetchArticles()
}

function handleCurrentChange() {
  fetchArticles()
}

function formatDate(date) {
  return new Date(date).toLocaleDateString('zh-CN')
}

function getAiTagType(ratio) {
  if (ratio > 0.7) return 'danger'
  if (ratio > 0.4) return 'warning'
  return 'success'
}
</script>

<style lang="scss" scoped>
.article-list {
  .toolbar {
    display: flex;
    gap: 20px;
    align-items: center;
    margin-bottom: 20px;
    flex-wrap: wrap;
  }

  .ai-ratio-filter {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .filter-label {
    font-size: 14px;
    color: $color-text-secondary;
  }

  .ratio-value {
    font-size: 14px;
    color: $color-text;
    min-width: 80px;
  }

  .table-container {
    padding: 20px;
  }

  .article-link {
    display: flex;
    align-items: center;
    gap: 12px;
    text-decoration: none;
    color: inherit;

    &:hover .article-title {
      color: $color-primary;
    }
  }

  .article-thumb {
    width: 40px;
    height: 40px;
    border-radius: $radius-sm;
    object-fit: cover;
    flex-shrink: 0;
  }

  .article-title {
    font-size: 14px;
    transition: color $transition-fast;
    overflow: hidden;
    text-overflow: ellipsis;
    white-space: nowrap;
  }

  .pagination {
    margin-top: 20px;
    display: flex;
    justify-content: flex-end;
  }
}
</style>
