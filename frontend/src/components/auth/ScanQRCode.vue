<template>
  <el-dialog
    :model-value="modelValue"
    title="扫码添加账号"
    width="360px"
    @close="$emit('close')"
  >
    <div class="qr-container">
      <div class="qr-placeholder">
        <el-icon :size="120" color="#ccc"><Picture /></el-icon>
        <p>等待扫码...</p>
      </div>
    </div>
  </el-dialog>
</template>

<script setup>
import { Picture } from '@element-plus/icons-vue'

defineProps({
  modelValue: Boolean
})

defineEmits(['close'])
</script>

<style lang="scss" scoped>
.qr-container {
  display: flex;
  justify-content: center;
  padding: 20px;
}

.qr-placeholder {
  text-align: center;

  p {
    margin-top: 16px;
    color: $color-text-secondary;
    font-size: 14px;
  }
}
</style>
