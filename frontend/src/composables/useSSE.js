import { ref, onUnmounted } from 'vue'

export function useSSE(url, onMessage) {
  const eventSource = ref(null)
  const connected = ref(false)
  const error = ref(null)

  function connect() {
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
      // Auto reconnect after 5 seconds
      setTimeout(connect, 5000)
    }
  }

  function disconnect() {
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
