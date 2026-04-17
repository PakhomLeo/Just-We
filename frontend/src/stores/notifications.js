import { defineStore } from 'pinia'
import { ref, computed } from 'vue'
import {
  deleteNotification,
  getNotifications,
  markAllNotificationsRead,
  markNotificationRead
} from '@/api/notifications'

export const useNotificationsStore = defineStore('notifications', () => {
  const notifications = ref([])
  const loading = ref(false)
  const unreadCount = ref(0)
  const unreadItems = computed(() => notifications.value.filter(n => !n.is_read))

  async function fetchNotifications(params = {}) {
    loading.value = true
    try {
      const response = await getNotifications({ page: 1, page_size: 20, ...params })
      notifications.value = response.data?.items || []
      unreadCount.value = response.data?.unread_count || 0
    } finally {
      loading.value = false
    }
  }

  async function markAsRead(id) {
    const notification = notifications.value.find(n => n.id === id)
    if (notification && !notification.is_read) {
      await markNotificationRead(id)
      notification.is_read = true
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
  }

  async function markAllAsRead() {
    await markAllNotificationsRead()
    notifications.value = notifications.value.map(item => ({ ...item, is_read: true }))
    unreadCount.value = 0
  }

  async function removeNotification(id) {
    await deleteNotification(id)
    const target = notifications.value.find(item => item.id === id)
    if (target && !target.is_read) {
      unreadCount.value = Math.max(0, unreadCount.value - 1)
    }
    notifications.value = notifications.value.filter(item => item.id !== id)
  }

  return {
    notifications,
    loading,
    unreadCount,
    unreadItems,
    fetchNotifications,
    markAsRead,
    markAllAsRead,
    removeNotification
  }
})
