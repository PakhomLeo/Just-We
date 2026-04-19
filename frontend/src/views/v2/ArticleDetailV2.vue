<template>
  <V2Page
    title="文章详情 / AI 三段解析"
    subtitle="默认展示清洗后的富文本，AI 文字、图片和类型判断分段审计。"
    watermark="ARTICLE"
    action-rail="文章详情功能：富文本预览 / 纯文本 / 原始载荷 / 重跑 AI / 查看图片解析 / 查看类型判断 / 打开原文"
  >
    <template #header-actions>
      <div class="v2-page-actions">
        <el-button @click="router.back()">返回列表</el-button>
        <el-button :disabled="!article?.url" @click="openUrl(article?.url)">打开原文</el-button>
        <el-button type="warning" :loading="reanalyzing" @click="reanalyze">重跑 AI</el-button>
      </div>
    </template>

    <el-skeleton v-if="loading" :rows="10" animated />
    <template v-else-if="article">
      <V2Section>
        <div class="hero">
          <div>
            <div class="pill-line">
              <V2StatusPill :label="article.ai_target_match ? `目标类型：${article.ai_target_match}` : '目标类型待判断'" :tone="article.ai_target_match === '是' ? 'success' : 'warning'" />
              <V2StatusPill :label="article.ai_analysis_status || 'AI 状态未知'" :tone="article.ai_analysis_status === 'success' ? 'success' : article.ai_analysis_status === 'failed' ? 'danger' : 'warning'" />
              <V2StatusPill :label="contentTypeLabel(article.content_type)" tone="purple" />
            </div>
            <h2>{{ article.title }}</h2>
            <p>{{ article.author || '-' }} · {{ formatDateTime(article.published_at) }} · 监测对象 #{{ article.monitored_account_id || '-' }}</p>
          </div>
          <div class="score-card">
            <strong>{{ formatPercent(article.ai_relevance_ratio) }}</strong>
            <span>AI 命中权重</span>
          </div>
        </div>
      </V2Section>

      <div class="detail-grid">
        <V2Section title="正文内容" subtitle="富文本只渲染清洗后的 content_html，不直接渲染 raw_content。">
          <el-tabs v-model="contentMode">
            <el-tab-pane label="富文本预览" name="rich">
              <div v-if="article.content_html" class="article-rich" v-html="article.content_html" />
              <V2Empty v-else title="暂无富文本" description="可切换到纯文本或原始载荷查看抓取结果。" />
            </el-tab-pane>
            <el-tab-pane label="纯文本" name="text">
              <div class="plain-content">{{ article.content || '暂无正文内容' }}</div>
            </el-tab-pane>
            <el-tab-pane label="原始载荷" name="payload">
              <div v-if="contentMode === 'payload'" class="payload-panel">
                <pre class="v2-json">{{ payloadJson }}</pre>
                <div class="raw-toolbar">
                  <span>raw_content：{{ rawContentSize }}</span>
                  <div class="v2-button-row">
                    <el-button size="small" :disabled="!article.raw_content" @click="rawPreviewLoaded = true">加载预览</el-button>
                    <el-button size="small" :disabled="!article.raw_content" @click="copyRawContent">复制全文</el-button>
                    <el-button size="small" :disabled="!article.raw_content" @click="downloadRawContent">下载 HTML</el-button>
                  </div>
                </div>
                <pre v-if="rawPreviewLoaded" class="raw-preview">{{ rawPreview }}</pre>
              </div>
            </el-tab-pane>
          </el-tabs>
        </V2Section>

        <V2Section title="AI pipeline" subtitle="按阶段展示 AI 处理进度。">
          <div class="ai-flow">
            <div
              v-for="stage in aiStages"
              :key="stage.key"
              class="ai-stage"
              :class="{ completed: stage.completed }"
            >
              <span>{{ stage.label }}</span>
              <small>{{ stage.completed ? '已完成' : '未完成' }}</small>
            </div>
          </div>
          <div class="pipeline-status">
            已完成 {{ completedAIStageCount }} / {{ aiStages.length }} 阶段
          </div>
          <div v-if="article.ai_analysis_error" class="v2-risk-note">AI 失败原因：{{ article.ai_analysis_error }}</div>
        </V2Section>
      </div>

      <V2Section title="图片资源" subtitle="展示本地化图片和原始图片地址，微信 CDN 应走图片代理。">
        <div class="image-grid" v-if="displayImages.length">
          <el-image v-for="image in displayImages" :key="image" :src="image" :preview-src-list="displayImages" fit="cover" />
        </div>
        <V2Empty v-else title="暂无图片" description="该文章没有解析到可展示图片。" />
      </V2Section>
    </template>
    <V2Empty v-else title="文章不存在" description="请返回文章列表重新选择。" />
  </V2Page>
</template>

<script setup>
import { computed, onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import V2Empty from '@/components/v2/V2Empty.vue'
import V2Page from '@/components/v2/V2Page.vue'
import V2Section from '@/components/v2/V2Section.vue'
import V2StatusPill from '@/components/v2/V2StatusPill.vue'
import { getArticle, reanalyzeArticleAI } from '@/api/articles'
import { formatDateTime, formatPercent } from './helpers'

const route = useRoute()
const router = useRouter()
const article = ref(null)
const loading = ref(false)
const reanalyzing = ref(false)
const contentMode = ref('rich')
const rawPreviewLoaded = ref(false)

const displayImages = computed(() => article.value?.images?.length ? article.value.images : (article.value?.original_images || []))
const aiStages = computed(() => [
  { key: 'text', label: '文字解析', completed: Boolean(article.value?.ai_text_analysis) },
  { key: 'image', label: '图片解析', completed: Boolean(article.value?.ai_image_analysis) || !displayImages.value.length },
  { key: 'type', label: '类型判断', completed: Boolean(article.value?.ai_type_judgment) },
  { key: 'combined', label: '合并结果', completed: Boolean(article.value?.ai_combined_analysis || article.value?.ai_judgment) }
])
const completedAIStageCount = computed(() => aiStages.value.filter(stage => stage.completed).length)
const payloadJson = computed(() => JSON.stringify({
  source_payload: article.value?.source_payload || null,
  metadata_json: article.value?.metadata_json || null,
  raw_content: {
    loaded: Boolean(article.value?.raw_content),
    length: article.value?.raw_content?.length || 0,
    preview_loaded: rawPreviewLoaded.value
  }
}, null, 2))
const rawContentSize = computed(() => {
  const length = article.value?.raw_content?.length || 0
  if (!length) return '无'
  if (length < 1024) return `${length} B`
  if (length < 1024 * 1024) return `${(length / 1024).toFixed(1)} KB`
  return `${(length / 1024 / 1024).toFixed(2)} MB`
})
const rawPreview = computed(() => {
  const content = article.value?.raw_content || ''
  if (content.length <= 50000) return content
  return `${content.slice(0, 50000)}\n\n... 已截断预览，完整内容请复制或下载。`
})

onMounted(() => {
  loadArticle()
  window.addEventListener('v2-reanalyze-current-article', reanalyze)
})
onUnmounted(() => window.removeEventListener('v2-reanalyze-current-article', reanalyze))

async function loadArticle() {
  loading.value = true
  try {
    const response = await getArticle(route.params.id)
    article.value = response.data
  } finally {
    loading.value = false
  }
}

async function reanalyze() {
  if (!article.value) return
  reanalyzing.value = true
  try {
    const response = await reanalyzeArticleAI(article.value.id)
    article.value = response.data
    ElMessage.success('AI 三段解析已重跑')
  } finally {
    reanalyzing.value = false
  }
}

async function copyRawContent() {
  if (!article.value?.raw_content) return
  await navigator.clipboard.writeText(article.value.raw_content)
  ElMessage.success('原始内容已复制')
}

function downloadRawContent() {
  if (!article.value?.raw_content) return
  const blob = new Blob([article.value.raw_content], { type: 'text/html;charset=utf-8' })
  const url = URL.createObjectURL(blob)
  const link = document.createElement('a')
  link.href = url
  link.download = `article-${article.value.id}-raw.html`
  link.click()
  URL.revokeObjectURL(url)
}

function openUrl(url) {
  if (url) window.open(url, '_blank', 'noopener,noreferrer')
}

function contentTypeLabel(value) {
  return ({ article: '普通文章', image_text: '图文消息', image_only: '纯图片', short_content: '短内容', audio: '音频', video: '视频', media_share: '媒体分享' })[value] || value || '未知类型'
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.hero {
  display: flex;
  justify-content: space-between;
  gap: 22px;

  h2 {
    margin: 16px 0 8px;
    font-size: 30px;
    font-weight: 950;
    letter-spacing: -0.04em;
  }

  p {
    color: $v2-muted;
    margin: 0;
    font-weight: 700;
  }
}

.pill-line {
  display: flex;
  flex-wrap: wrap;
  gap: 8px;
}

.score-card {
  min-width: 160px;
  border-radius: 28px;
  background: $v2-yellow;
  padding: 24px;
  text-align: center;

  strong {
    color: $v2-ink;
    display: block;
    font-size: 34px;
    font-weight: 950;
  }

  span {
    color: $v2-ink;
    font-weight: 900;
  }
}

.detail-grid {
  display: grid;
  grid-template-columns: minmax(0, 1.6fr) minmax(360px, 0.8fr);
  gap: 24px;
  margin: 24px 0;
}

.article-rich,
.plain-content {
  border-radius: 24px;
  background: $v2-card-soft;
  padding: 22px;
  line-height: 1.85;
  word-break: break-word;
}

.plain-content {
  white-space: pre-wrap;
}

.payload-panel {
  display: grid;
  gap: 14px;
}

.raw-toolbar {
  border-radius: 18px;
  background: $v2-card-soft;
  padding: 12px 14px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
  font-weight: 900;
  color: $v2-muted;
}

.raw-preview {
  max-height: 420px;
  overflow: auto;
  border-radius: 18px;
  background: $v2-card-soft;
  padding: 18px;
  white-space: pre-wrap;
  word-break: break-word;
}

.ai-flow {
  display: grid;
  gap: 10px;
  margin-bottom: 14px;
}

.ai-stage {
  border-radius: 22px;
  background: $v2-card-soft;
  color: $v2-ink;
  padding: 14px 16px;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-weight: 950;

  &.completed {
    background: $v2-yellow;
  }

  small {
    color: $v2-muted;
    font-size: 12px;
    font-weight: 900;
  }
}

.pipeline-status {
  border-radius: 18px;
  background: $v2-card-soft;
  color: $v2-muted;
  padding: 14px 16px;
  font-size: 13px;
  font-weight: 900;
}

.image-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 14px;

  .el-image {
    width: 100%;
    height: 150px;
    border-radius: 20px;
    overflow: hidden;
  }
}

@media (max-width: 1100px) {
  .detail-grid,
  .hero {
    grid-template-columns: 1fr;
    flex-direction: column;
  }
}
</style>
