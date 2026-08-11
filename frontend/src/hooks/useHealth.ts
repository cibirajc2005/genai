import { useEffect, useState } from 'react'
import { getHealth } from '../services/api'
import type { HealthResponse } from '../types/health'

export function useHealth() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const controller = new AbortController()
    getHealth(controller.signal).then(setHealth).catch((reason: unknown) => {
      if (reason instanceof DOMException && reason.name === 'AbortError') return
      setError(reason instanceof Error ? reason.message : 'Backend unavailable')
    })
    return () => controller.abort()
  }, [])

  return { health, error }
}

