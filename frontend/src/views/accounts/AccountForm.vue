<template>
  <el-dialog
    :model-value="modelValue"
    :title="account ? '编辑账号' : '添加账号'"
    width="500px"
    @close="$emit('close')"
  >
    <el-form ref="formRef" :model="form" :rules="rules" label-position="top">
      <el-form-item label="账号名称" prop="name">
        <el-input v-model="form.name" placeholder="请输入账号名称" />
      </el-form-item>

      <el-form-item label="Biz" prop="biz">
        <el-input v-model="form.biz" placeholder="请输入 biz" />
      </el-form-item>

      <el-form-item label="URL" prop="url">
        <el-input v-model="form.url" placeholder="请输入公众号URL" />
      </el-form-item>

      <el-form-item label="描述">
        <el-input v-model="form.description" type="textarea" :rows="3" />
      </el-form-item>
    </el-form>

    <template #footer>
      <el-button @click="$emit('close')">取消</el-button>
      <el-button type="primary" @click="handleSubmit" :loading="submitting">
        确定
      </el-button>
    </template>
  </el-dialog>
</template>

<script setup>
import { ref, reactive, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { createAccount, updateAccount } from '@/api/accounts'

const props = defineProps({
  modelValue: Boolean,
  account: Object
})

const emit = defineEmits(['close'])

const formRef = ref(null)
const submitting = ref(false)

const form = reactive({
  name: '',
  biz: '',
  url: '',
  description: ''
})

const rules = {
  name: [{ required: true, message: '请输入账号名称', trigger: 'blur' }],
  biz: [{ required: true, message: '请输入 biz', trigger: 'blur' }]
}

watch(() => props.account, (newAccount) => {
  if (newAccount) {
    Object.assign(form, {
      name: newAccount.name,
      biz: newAccount.biz,
      url: newAccount.url || '',
      description: newAccount.description || ''
    })
  } else {
    Object.assign(form, {
      name: '',
      biz: '',
      url: '',
      description: ''
    })
  }
}, { immediate: true })

async function handleSubmit() {
  try {
    await formRef.value.validate()
    submitting.value = true

    if (props.account) {
      await updateAccount(props.account.id, form)
      ElMessage.success('更新成功')
    } else {
      await createAccount(form)
      ElMessage.success('添加成功')
    }

    emit('close')
  } catch (error) {
    // Validation failed
  } finally {
    submitting.value = false
  }
}
</script>
