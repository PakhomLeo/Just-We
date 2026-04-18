<template>
  <div class="v2-login">
    <div class="login-stage">
      <div class="login-copy">
        <h1>公众号监测<br>与 AI 分析控制台</h1>
        <strong>monitor what matters</strong>
        <p>账号绑定、公众号解析、文章下载、三段式 AI 判断和 Feed 输出，在同一个后台闭环完成。</p>
      </div>

      <form class="login-card" @submit.prevent="handleSubmit">
        <div class="login-card__header">
          <h2>{{ isRegisterMode ? '注册 Just-We' : '登录 Just-We' }}</h2>
          <div class="auth-mode" aria-label="认证方式">
            <button
              :class="{ active: !isRegisterMode }"
              type="button"
              @click="setMode(false)"
            >
              登录
            </button>
            <button
              :class="{ active: isRegisterMode }"
              type="button"
              @click="setMode(true)"
            >
              注册
            </button>
          </div>
        </div>
        <label>
          <span>{{ isRegisterMode ? '邮箱' : '邮箱或用户名' }}</span>
          <input
            v-model.trim="form.email"
            :autocomplete="isRegisterMode ? 'email' : 'username'"
            placeholder="admin@example.com"
          >
        </label>
        <label>
          <span>密码</span>
          <input
            v-model="form.password"
            :autocomplete="isRegisterMode ? 'new-password' : 'current-password'"
            placeholder="至少 8 位密码"
            type="password"
          >
        </label>
        <button class="submit-button" :disabled="loading || !form.email || !form.password" type="submit">
          {{ submitText }}
        </button>
        <p v-if="errorMessage" class="login-error">{{ errorMessage }}</p>
        <p class="login-note">
          {{ isRegisterMode ? '已有账号？' : '还没有账号？' }}
          <button class="switch-link" type="button" @click="setMode(!isRegisterMode)">
            {{ isRegisterMode ? '返回登录' : '创建账号' }}
          </button>
        </p>
      </form>
    </div>
  </div>
</template>

<script setup>
import { computed, reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useAuthStore } from '@/stores/auth'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const errorMessage = ref('')
const isRegisterMode = ref(false)
const loading = ref(false)
const form = reactive({
  email: '',
  password: ''
})

const submitText = computed(() => {
  if (loading.value) {
    return isRegisterMode.value ? '注册中...' : '登录中...'
  }
  return isRegisterMode.value ? '创建并进入系统' : '进入系统'
})

function setMode(nextMode) {
  isRegisterMode.value = nextMode
  errorMessage.value = ''
}

async function handleSubmit() {
  errorMessage.value = ''
  loading.value = true
  try {
    const payload = {
      email: form.email,
      password: form.password
    }
    if (isRegisterMode.value) {
      await authStore.register({ ...payload, role: 'viewer' })
    } else {
      await authStore.login(payload)
    }
    router.push(route.query.redirect || '/dashboard')
  } catch (error) {
    errorMessage.value = error?.response?.data?.detail || error?.response?.data?.error || (isRegisterMode.value ? '注册失败，请检查邮箱、密码或网络连接。' : '登录失败，请检查账号、密码或网络连接。')
  } finally {
    loading.value = false
  }
}
</script>

<style lang="scss" scoped>
@use '@/assets/styles/v2/tokens' as *;

.v2-login {
  display: grid;
  place-items: center;
  min-height: 100vh;
  padding: 32px;
  background: #dfeaf2;
}

.login-stage {
  position: relative;
  width: min(1280px, 100%);
  min-height: min(760px, calc(100vh - 64px));
  border-radius: 34px;
  overflow: hidden;
  background:
    radial-gradient(circle at 22% 20%, rgba(#fff, 0.34), transparent 26%),
    linear-gradient(145deg, #c7d8e6 0%, #9eb9d3 46%, #789fc7 100%);
  display: grid;
  grid-template-columns: minmax(0, 1fr) minmax(360px, 460px);
  align-items: center;
  gap: clamp(32px, 6vw, 84px);
  padding: clamp(36px, 7vw, 96px);
  box-shadow: $v2-shadow-soft;
}

.login-copy {
  color: #fff;
  max-width: 620px;
  text-align: left;
  text-shadow: 0 10px 30px rgba(#26445c, 0.16);

  h1 {
    margin: 0;
    font-size: clamp(44px, 7vw, 88px);
    line-height: 1.08;
    font-weight: 950;
    letter-spacing: 0;
  }

  strong {
    display: block;
    margin-top: 24px;
    color: #f2df67;
    font-size: clamp(24px, 4vw, 42px);
    font-weight: 950;
    line-height: 1.1;
  }

  p {
    max-width: 560px;
    margin: 22px 0 0;
    color: rgba(#fff, 0.9);
    font-size: 16px;
    line-height: 1.8;
    font-weight: 700;
  }
}

.login-card {
  position: relative;
  z-index: 1;
  width: 100%;
  border-radius: 28px;
  background: rgba(#fff, 0.86);
  backdrop-filter: blur(22px);
  padding: 30px 32px;
  display: grid;
  gap: 16px;
  box-shadow: 0 24px 70px rgba($v2-ink, 0.16);

  h2 {
    margin: 0;
    color: $v2-ink;
    font-size: 20px;
    font-weight: 950;
  }

  &__header {
    display: grid;
    gap: 16px;
  }

  label {
    display: grid;
    gap: 6px;
    color: $v2-muted;
    font-size: 12px;
    font-weight: 900;
  }

  input {
    width: 100%;
    border: 0;
    border-radius: 18px;
    background: $v2-card-soft;
    color: $v2-ink;
    padding: 14px 16px;
    outline: none;
    font: inherit;
  }
}

.auth-mode {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 6px;
  border-radius: 999px;
  background: rgba(#d9e6ef, 0.78);
  padding: 5px;

  button {
    min-height: 38px;
    border: 0;
    border-radius: 999px;
    background: transparent;
    color: $v2-muted;
    font: inherit;
    font-weight: 950;
    cursor: pointer;

    &.active {
      background: #fff;
      color: $v2-ink;
      box-shadow: 0 8px 18px rgba($v2-ink, 0.08);
    }
  }
}

.submit-button {
  border: 0;
  border-radius: 999px;
  background: $v2-yellow;
  color: $v2-ink;
  min-height: 50px;
  font: inherit;
  font-weight: 950;
  cursor: pointer;

  &:disabled {
    opacity: 0.55;
    cursor: not-allowed;
  }
}

.login-error {
  margin: 0;
  color: $v2-orange;
  font-size: 13px;
  font-weight: 900;
}

.login-note {
  margin: 0;
  color: $v2-muted;
  font-size: 12px;
  font-weight: 700;
  text-align: center;
}

.switch-link {
  border: 0;
  background: transparent;
  color: $v2-ink;
  padding: 0;
  font: inherit;
  font-weight: 950;
  cursor: pointer;
}

@media (max-width: 1180px) {
  .v2-login {
    padding: 16px;
  }

  .login-stage {
    min-height: calc(100vh - 32px);
    grid-template-columns: 1fr;
    align-content: center;
    padding: 34px 22px;
  }

  .login-copy {
    text-align: center;

    h1 {
      font-size: clamp(34px, 12vw, 58px);
    }

    strong {
      margin-top: 16px;
      font-size: clamp(22px, 8vw, 34px);
    }

    p {
      margin-right: auto;
      margin-left: auto;
      font-size: 14px;
    }
  }

  .login-card {
    padding: 24px;
  }
}
</style>
