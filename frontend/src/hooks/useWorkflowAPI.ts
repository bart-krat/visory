import { useState } from 'react'

// API base URL - empty for local dev (uses Vite proxy), set for production
const API_BASE = import.meta.env.VITE_API_URL || ''

export function useWorkflowAPI(sessionId: string | null) {
  const [loading, setLoading] = useState(false)

  const startQuestionnaire = async () => {
    if (!sessionId) return null
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/utility/start?session_id=${sessionId}`, { method: 'POST' })
      const data = await res.json()
      return data
    } catch (error) {
      console.error('Error starting questionnaire:', error)
      return { error: 'Error starting questionnaire' }
    } finally {
      setLoading(false)
    }
  }

  const startPlanning = async () => {
    if (!sessionId) return null
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/planning/start?session_id=${sessionId}`, { method: 'POST' })
      const data = await res.json()
      return data
    } catch (error) {
      console.error('Error starting planning:', error)
      return { error: 'Error starting planning' }
    } finally {
      setLoading(false)
    }
  }

  const fetchWorkflowState = async () => {
    if (!sessionId) return null
    try {
      const res = await fetch(`${API_BASE}/api/workflow/${sessionId}/state`)
      const data = await res.json()
      return data
    } catch (error) {
      console.error('Failed to fetch workflow state:', error)
      return null
    }
  }

  const navigateToPhase = async (targetPhase: string) => {
    if (!sessionId) return null
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/workflow/navigate?session_id=${sessionId}&target_phase=${targetPhase}`, {
        method: 'POST',
      })
      const data = await res.json()
      return data
    } catch (error) {
      console.error('Error navigating to phase:', error)
      return { error: 'Error navigating to phase' }
    } finally {
      setLoading(false)
    }
  }

  const sendMessage = async (message: string, phase: string) => {
    if (!sessionId) return null
    setLoading(true)
    try {
      if (phase === 'questionnaire') {
        const res = await fetch(`${API_BASE}/api/utility/message`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, message })
        })
        const data = await res.json()
        return { type: 'json', data }
      } else {
        // Streaming response
        const res = await fetch(`${API_BASE}/api/workflow/message`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, message })
        })
        return { type: 'stream', response: res }
      }
    } catch (error) {
      console.error('Error sending message:', error)
      return { error: 'Error connecting to server' }
    } finally {
      if (phase === 'questionnaire') {
        setLoading(false)
      }
      // For streaming, loading is set to false after stream completes (handled in component)
    }
  }

  const submitTaskDurationsAndTimes = async (
    tasks: Array<{ name: string; duration: number; time_slot: string | null }>,
    timeWindowStart: string,
    timeWindowEnd: string
  ) => {
    if (!sessionId) return null
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/workflow/constraints`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          tasks,
          time_window_start: timeWindowStart,
          time_window_end: timeWindowEnd,
        })
      })
      const data = await res.json()
      return data
    } catch (error) {
      console.error('Error submitting constraints:', error)
      return { error: 'Error submitting constraints' }
    } finally {
      setLoading(false)
    }
  }

  const submitOptimizationConstraints = async (
    constraintIds: string[],
    customConstraint: string | null
  ) => {
    if (!sessionId) return null
    setLoading(true)
    try {
      const res = await fetch(`${API_BASE}/api/constraints/submit`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          constraint_ids: constraintIds,
          custom_constraint: customConstraint,
        })
      })
      const data = await res.json()
      return data
    } catch (error) {
      console.error('Error running optimization:', error)
      return { error: 'Error running optimization' }
    } finally {
      setLoading(false)
    }
  }

  const fetchConstraintOptions = async () => {
    if (!sessionId) return null
    try {
      const res = await fetch(`${API_BASE}/api/constraints/options/${sessionId}`)
      const data = await res.json()
      return data
    } catch (error) {
      console.error('Failed to fetch constraint options:', error)
      return null
    }
  }

  return {
    loading,
    setLoading,
    startQuestionnaire,
    startPlanning,
    fetchWorkflowState,
    navigateToPhase,
    sendMessage,
    submitTaskDurationsAndTimes,
    submitOptimizationConstraints,
    fetchConstraintOptions,
  }
}
