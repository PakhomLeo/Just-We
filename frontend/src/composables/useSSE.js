import { ref, onUnmounted } from 'vue'

export function useSSE(url, onMessage) {
  const eventSource = ref(null)
  const connected = ref(false)
  const error = ref(null)
  const reconnectTimer = ref(null)
  const manuallyDisconnected = ref(false)

  function clearReconnectTimer() {
    if (reconnectTimer.value) {
      clearTimeout(reconnectTimer.value)
      reconnectTimer.value = null
    }
  }

  function connect() {
    manuallyDisconnected.value = false
    clearReconnectTimer()

    if (eventSource.value) {
      eventSource.value.close()
    }

    eventSource.value = new EventSource(url)

    eventSource.value.onopen = () => {
      connected.value = true
      error.value = null
    }

    eventSource.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        onMessage(data)
      } catch (e) {
        onMessage(event.data)
      }
    }

    eventSource.value.onerror = (e) => {
      connected.value = false
      error.value = e

      if (!manuallyDisconnected.value) {
        reconnectTimer.value = setTimeout(() => {
          reconnectTimer.value = null
          connect()
        }, 5000)
      }
    }
  }

  function disconnect() {
    manuallyDisconnected.value = true
    clearReconnectTimer()

    if (eventSource.value) {
      eventSource.value.close()
      eventSource.value = null
      connected.value = false
    }
  }

  onUnmounted(() => {
    disconnect()
  })

  return {
    connected,
    error,
    connect,
    disconnect
  }
}
