import { useEffect, useRef, useState, useCallback } from 'react'
import type { WorkerEvent, WebSocketMessage } from '../types'

type ConnectionStatus = 'connecting' | 'connected' | 'disconnected'

interface UseWebSocketReturn {
  status: ConnectionStatus
  events: WorkerEvent[]
  lastEvent: WorkerEvent | null
  clearEvents: () => void
}

const MAX_EVENTS = 200

export function useWebSocket(url: string): UseWebSocketReturn {
  const [status, setStatus] = useState<ConnectionStatus>('connecting')
  const [events, setEvents] = useState<WorkerEvent[]>([])
  const [lastEvent, setLastEvent] = useState<WorkerEvent | null>(null)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectTimeoutRef = useRef<number | undefined>(undefined)

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        setStatus('connected')
        console.log('[WS] Connected')
      }

      ws.onmessage = (evt) => {
        try {
          const msg: WebSocketMessage = JSON.parse(evt.data)
          if (msg.type === 'event') {
            const event = msg.data as WorkerEvent
            setEvents((prev) => [event, ...prev].slice(0, MAX_EVENTS))
            setLastEvent(event)
          }
        } catch (err) {
          console.error('[WS] Parse error:', err)
        }
      }

      ws.onclose = () => {
        setStatus('disconnected')
        console.log('[WS] Disconnected, reconnecting in 2s...')
        reconnectTimeoutRef.current = window.setTimeout(connect, 2000)
      }

      ws.onerror = () => {
        ws.close()
      }
    } catch (err) {
      console.error('[WS] Connect error:', err)
      setStatus('disconnected')
      reconnectTimeoutRef.current = window.setTimeout(connect, 2000)
    }
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectTimeoutRef.current) {
        window.clearTimeout(reconnectTimeoutRef.current)
      }
      wsRef.current?.close()
    }
  }, [connect])

  const clearEvents = useCallback(() => {
    setEvents([])
  }, [])

  return { status, events, lastEvent, clearEvents }
}