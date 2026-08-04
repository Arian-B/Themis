/**
 * hooks/useNegotiationStream.ts — WebSocket hook for real-time negotiation streaming.
 *
 * Manages the WebSocket lifecycle for the NegotiationViewer component.
 * Connects to WS /api/v1/negotiate/stream/:sessionId, receives Redline JSON
 * objects, and appends them to a local state array.
 *
 * Features:
 *   - Auto-reconnect with exponential backoff (max 3 retries)
 *   - Connection status: 'connecting' | 'open' | 'closed' | 'error'
 *   - Cleans up WebSocket on component unmount (no memory leaks)
 *
 * Usage:
 *   const { redlines, status } = useNegotiationStream(sessionId)
 *
 * TODO (Phase 4): Implement using native WebSocket API.
 */

import { useEffect, useRef, useState } from 'react'

type ConnectionStatus = 'idle' | 'connecting' | 'open' | 'closed' | 'error'

interface UseNegotiationStreamReturn {
  redlines: unknown[]
  status: ConnectionStatus
  error: string | null
}

export function useNegotiationStream(sessionId: string | null): UseNegotiationStreamReturn {
  const [redlines, setRedlines] = useState<unknown[]>([])
  const [status, setStatus] = useState<ConnectionStatus>('idle')
  const [error, setError] = useState<string | null>(null)
  const wsRef = useRef<WebSocket | null>(null)

  useEffect(() => {
    if (!sessionId) return

    // TODO (Phase 4): Open WS connection to /ws/negotiate/stream/:sessionId
    // Handle onmessage: parse JSON, append to redlines
    // Handle onerror: set error state
    // Handle onclose: set closed state, trigger retry if needed
    // Return cleanup: wsRef.current?.close()

    return () => {
      wsRef.current?.close()
    }
  }, [sessionId])

  return { redlines, status, error }
}
