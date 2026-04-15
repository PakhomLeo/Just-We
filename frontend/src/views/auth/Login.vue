<template>
  <div class="login-page">
    <div class="login-card">
      <div class="login-left">
        <div class="brand">
          <img src="@/assets/images/logo.svg" alt="Logo" class="logo">
          <h1 class="brand-name">DynamicWePubMonitor</h1>
        </div>

        <div class="features">
          <div class="feature-item">
            <el-icon :size="24" color="#FF6B00"><Odometer /></el-icon>
            <div>
              <h3>实时监控</h3>
              <p>微信公众号权重智能监测</p>
            </div>
          </div>
          <div class="feature-item">
            <el-icon :size="24" color="#FF6B00"><TrendCharts /></el-icon>
            <div>
              <h3>数据分析</h3>
              <p>多维度数据统计与可视化</p>
            </div>
          </div>
          <div class="feature-item">
            <el-icon :size="24" color="#FF6B00"><Clock /></el-icon>
            <div>
              <h3>智能调度</h3>
              <p>自动抓取与异常告警</p>
            </div>
          </div>
        </div>
      </div>

      <div class="login-right">
        <el-tabs v-model="activeTab" class="login-tabs">
          <el-tab-pane label="登录" name="login">
            <el-form ref="loginFormRef" :model="loginForm" :rules="loginRules" label-position="top">
              <el-form-item prop="username">
                <el-input
                  v-model="loginForm.username"
                  placeholder="用户名"
                  size="large"
                  :prefix-icon="User"
                />
              </el-form-item>

              <el-form-item prop="password">
                <el-input
                  v-model="loginForm.password"
                  type="password"
                  placeholder="密码"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                />
              </el-form-item>

              <el-form-item>
                <el-button type="primary" size="large" class="login-btn" @click="handleLogin">
                  登录
                </el-button>
              </el-form-item>

              <div class="forgot-password">
                <span @click="showResetDialog = true">忘记密码？</span>
              </div>
            </el-form>
          </el-tab-pane>

          <el-tab-pane label="注册" name="register">
            <el-form ref="registerFormRef" :model="registerForm" :rules="registerRules" label-position="top">
              <el-form-item prop="username">
                <el-input
                  v-model="registerForm.username"
                  placeholder="用户名"
                  size="large"
                  :prefix-icon="User"
                />
              </el-form-item>

              <el-form-item prop="email">
                <el-input
                  v-model="registerForm.email"
                  placeholder="邮箱"
                  size="large"
                  :prefix-icon="Message"
                />
              </el-form-item>

              <el-form-item prop="password">
                <el-input
                  v-model="registerForm.password"
                  type="password"
                  placeholder="密码"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                />
              </el-form-item>

              <el-form-item prop="confirmPassword">
                <el-input
                  v-model="registerForm.confirmPassword"
                  type="password"
                  placeholder="确认密码"
                  size="large"
                  :prefix-icon="Lock"
                  show-password
                />
              </el-form-item>

              <el-form-item>
                <el-button type="primary" size="large" class="login-btn" @click="handleRegister">
                  注册
                </el-button>
              </el-form-item>
            </el-form>
          </el-tab-pane>
        </el-tabs>
      </div>
    </div>

    <el-dialog v-model="showResetDialog" title="重置密码" width="400px" :close-on-click-modal="false">
      <el-form :model="resetForm" label-position="top">
        <el-form-item label="邮箱">
          <el-input v-model="resetForm.email" placeholder="请输入注册邮箱" size="large" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showResetDialog = false">取消</el-button>
        <el-button type="primary" @click="handleReset">发送重置链接</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, reactive } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { useAuthStore } from '@/stores/auth'
import { ElMessage } from 'element-plus'
import { User, Lock, Message, Odometer, TrendCharts, Clock } from '@element-plus/icons-vue'

const router = useRouter()
const route = useRoute()
const authStore = useAuthStore()

const activeTab = ref('login')
const showResetDialog = ref(false)
const loginFormRef = ref(null)
const registerFormRef = ref(null)

const loginForm = reactive({
  username: '',
  password: ''
})

const registerForm = reactive({
  username: '',
  email: '',
  password: '',
  confirmPassword: ''
})

const resetForm = reactive({
  email: ''
})

const loginRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}

const registerRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  email: [
    { required: true, message: '请输入邮箱', trigger: 'blur' },
    { type: 'email', message: '请输入有效邮箱', trigger: 'blur' }
  ],
  password: [
    { required: true, message: '请输入密码', trigger: 'blur' },
    { min: 6, message: '密码至少6位', trigger: 'blur' }
  ],
  confirmPassword: [
    { required: true, message: '请确认密码', trigger: 'blur' },
    {
      validator: (rule, value, callback) => {
        if (value !== registerForm.password) {
          callback(new Error('两次密码不一致'))
        } else {
          callback()
        }
      },
      trigger: 'blur'
    }
  ]
}

async function handleLogin() {
  try {
    await loginFormRef.value.validate()
    await authStore.login(loginForm)
    const redirect = route.query.redirect || '/dashboard'
    router.push(redirect)
  } catch (error) {
    // Validation error or login failed
  }
}

async function handleRegister() {
  try {
    await registerFormRef.value.validate()
    await authStore.register({
      username: registerForm.username,
      email: registerForm.email,
      password: registerForm.password
    })
    ElMessage.success('注册成功')
    router.push('/dashboard')
  } catch (error) {
    // Validation error or registration failed
  }
}

function handleReset() {
  ElMessage.success('重置链接已发送到邮箱')
  showResetDialog.value = false
}
</script>

<style lang="scss" scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: $color-bg;
  padding: 20px;
}

.login-card {
  display: flex;
  width: 900px;
  max-width: 100%;
  background: $color-card;
  border-radius: $radius-lg;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.1);
  overflow: hidden;
}

.login-left {
  flex: 0 0 60%;
  padding: 48px;
  background: linear-gradient(135deg, $color-bg 0%, darken($color-bg, 5%) 100%);

  .brand {
    display: flex;
    align-items: center;
    gap: 16px;
    margin-bottom: 48px;
  }

  .logo {
    width: 48px;
    height: 48px;
  }

  .brand-name {
    font-size: 24px;
    font-weight: 700;
    color: $color-text;
  }
}

.features {
  display: flex;
  flex-direction: column;
  gap: 24px;
}

.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 16px;

  h3 {
    font-size: 16px;
    font-weight: 600;
    color: $color-text;
    margin-bottom: 4px;
  }

  p {
    font-size: 14px;
    color: $color-text-secondary;
  }
}

.login-right {
  flex: 0 0 40%;
  padding: 48px;
}

.login-tabs {
  :deep(.el-tabs__header) {
    margin-bottom: 32px;
  }

  :deep(.el-tabs__item) {
    font-size: 18px;
    font-weight: 600;

    &.is-active {
      color: $color-primary;
    }
  }

  :deep(.el-tabs__active-bar) {
    background-color: $color-primary;
  }
}

.login-btn {
  width: 100%;
  height: 48px;
  font-size: 16px;
  border-radius: $radius-sm;
}

.forgot-password {
  text-align: center;
  margin-top: 16px;

  span {
    color: $color-primary;
    cursor: pointer;

    &:hover {
      text-decoration: underline;
    }
  }
}
</style>
