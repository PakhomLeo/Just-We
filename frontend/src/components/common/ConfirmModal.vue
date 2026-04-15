<template>
  <el-dialog
    :model-value="modelValue"
    :title="title"
    :width="width"
    :close-on-click-modal="false"
    @close="$emit('close')"
  >
    <slot>{{ message }}</slot>
    <template #footer>
      <slot name="footer">
        <el-button @click="$emit('close')">取消</el-button>
        <el-button :type="confirmType" :loading="loading" @click="handleConfirm">
          {{ confirmText }}
        </el-button>
      </slot>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref } from 'vue'

const props = defineProps({
  modelValue: Boolean,
  title: {
    type: String,
    default: '确认'
  },
  message: String,
  confirmText: {
    type: String,
    default: '确定'
  },
  confirmType: {
    type: String,
    default: 'primary'
  },
  width: {
    type: String,
    default: '400px'
  }
})

const emit = defineEmits(['close', 'confirm'])
const loading = ref(false)

async function handleConfirm() {
  emit('confirm')
}
</script>
