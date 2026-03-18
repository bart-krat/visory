import { useState, useEffect } from 'react'

type Message = { role: 'user' | 'assistant'; content: string }
type ConstraintOption = { id: string; label: string; description: string }
type TaskForConstraints = {
  name: string
  category: string
  duration: number
  time_slot: string
}

export default function ChatView() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [phase, setPhase] = useState<string>('')
  const [constraintOptions, setConstraintOptions] = useState<ConstraintOption[]>([])

  // Constraints table state
  const [tasksForConstraints, setTasksForConstraints] = useState<TaskForConstraints[]>([])
  const [timeWindowStart, setTimeWindowStart] = useState('09:00')
  const [timeWindowEnd, setTimeWindowEnd] = useState('17:00')

  // Start workflow on mount
  useEffect(() => {
    const startWorkflow = async () => {
      try {
        const res = await fetch('/api/workflow/start', { method: 'POST' })
        const data = await res.json()
        setSessionId(data.session_id)
        setPhase(data.phase)
        setMessages([{ role: 'assistant', content: data.message }])
      } catch {
        setMessages([{ role: 'assistant', content: 'Error starting workflow. Is the server running?' }])
      }
    }
    startWorkflow()
  }, [])

  // Fetch tasks when entering constraints phase
  useEffect(() => {
    if (phase === 'constraints' && sessionId) {
      const fetchTasks = async () => {
        try {
          const res = await fetch(`/api/workflow/${sessionId}/state`)
          const data = await res.json()
          setTasksForConstraints(
            data.tasks.map((t: any) => ({
              name: t.name,
              category: t.category,
              duration: t.duration || 30,
              time_slot: '',
            }))
          )
        } catch {
          console.error('Failed to fetch tasks')
        }
      }
      fetchTasks()
    }
  }, [phase, sessionId])

  // Fetch constraint options when entering constraint_clarification phase
  useEffect(() => {
    if (phase === 'constraint_clarification') {
      const fetchOptions = async () => {
        try {
          const res = await fetch('/api/constraints/options')
          const data = await res.json()
          setConstraintOptions(data.options)
        } catch {
          console.error('Failed to fetch constraint options')
        }
      }
      fetchOptions()
    } else {
      setConstraintOptions([])
    }
  }, [phase])

  // Fetch current phase from server
  const fetchCurrentPhase = async () => {
    if (!sessionId) return
    try {
      const res = await fetch(`/api/workflow/${sessionId}/state`)
      const data = await res.json()
      setPhase(data.phase)
    } catch {
      console.error('Failed to fetch workflow state')
    }
  }

  const send = async (message?: string) => {
    const msgToSend = message ?? input
    if (!msgToSend.trim() || !sessionId) return

    const userMsg: Message = { role: 'user', content: msgToSend }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/workflow/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: msgToSend })
      })

      const reader = res.body?.getReader()
      if (!reader) throw new Error('No reader')

      const decoder = new TextDecoder()
      let assistantContent = ''

      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        assistantContent += chunk

        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: assistantContent }
          return updated
        })
      }

      await fetchCurrentPhase()

    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error connecting to server' }])
    }
    setLoading(false)
  }

  const handleConstraintSelect = (option: ConstraintOption) => {
    send(option.id)
  }

  const updateTaskDuration = (index: number, duration: string) => {
    setTasksForConstraints(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], duration: parseInt(duration) || 0 }
      return updated
    })
  }

  const updateTaskTimeSlot = (index: number, timeSlot: string) => {
    setTasksForConstraints(prev => {
      const updated = [...prev]
      updated[index] = { ...updated[index], time_slot: timeSlot }
      return updated
    })
  }

  const submitConstraints = async () => {
    if (!sessionId) return

    // Validate all durations are set
    const invalidTasks = tasksForConstraints.filter(t => !t.duration || t.duration <= 0)
    if (invalidTasks.length > 0) {
      alert('Please set a duration for all tasks')
      return
    }

    setLoading(true)

    try {
      const res = await fetch('/api/workflow/constraints', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          tasks: tasksForConstraints.map(t => ({
            name: t.name,
            duration: t.duration,
            time_slot: t.time_slot || null,
          })),
          time_window_start: timeWindowStart,
          time_window_end: timeWindowEnd,
        })
      })

      const data = await res.json()

      // Add a summary message
      const summary = tasksForConstraints
        .map(t => `${t.name}: ${t.duration} min${t.time_slot ? ` @ ${t.time_slot}` : ''}`)
        .join('\n')
      setMessages(prev => [
        ...prev,
        { role: 'user', content: `Time window: ${timeWindowStart} - ${timeWindowEnd}\n\n${summary}` },
        { role: 'assistant', content: data.message }
      ])

      setPhase(data.phase)
      setTasksForConstraints([])

    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error submitting constraints' }])
    }

    setLoading(false)
  }

  const getCategoryEmoji = (category: string) => {
    return { health: '💪', work: '💼', leisure: '🎮' }[category] || '📌'
  }

  return (
    <div>
      {phase && (
        <div style={{ marginBottom: 8, fontSize: 12, color: '#666' }}>
          Phase: {phase}
        </div>
      )}
      <div style={{ border: '1px solid #ccc', borderRadius: 8, padding: 16, minHeight: 300, marginBottom: 16 }}>
        {messages.map((m, i) => (
          <div key={i} style={{ marginBottom: 12, textAlign: m.role === 'user' ? 'right' : 'left' }}>
            <span style={{
              background: m.role === 'user' ? '#007bff' : '#e9ecef',
              color: m.role === 'user' ? '#fff' : '#000',
              padding: '8px 12px',
              borderRadius: 16,
              display: 'inline-block',
              maxWidth: '80%',
              whiteSpace: 'pre-wrap'
            }}>
              {m.content}
            </span>
          </div>
        ))}
        {loading && <div style={{ color: '#666' }}>Thinking...</div>}

        {/* Constraints Table */}
        {phase === 'constraints' && tasksForConstraints.length > 0 && !loading && (
          <div style={{ marginTop: 16, padding: 16, background: '#f8f9fa', borderRadius: 8 }}>
            <h4 style={{ margin: '0 0 12px 0', fontSize: 14 }}>Set task durations and optional fixed times:</h4>

            <table style={{ width: '100%', borderCollapse: 'collapse', marginBottom: 16 }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #dee2e6' }}>
                  <th style={{ textAlign: 'left', padding: 8 }}>Task</th>
                  <th style={{ textAlign: 'left', padding: 8 }}>Category</th>
                  <th style={{ textAlign: 'left', padding: 8 }}>Duration (min)*</th>
                  <th style={{ textAlign: 'left', padding: 8 }}>Fixed Time (optional)</th>
                </tr>
              </thead>
              <tbody>
                {tasksForConstraints.map((task, idx) => (
                  <tr key={idx} style={{ borderBottom: '1px solid #dee2e6' }}>
                    <td style={{ padding: 8 }}>{task.name}</td>
                    <td style={{ padding: 8 }}>{getCategoryEmoji(task.category)} {task.category}</td>
                    <td style={{ padding: 8 }}>
                      <input
                        type="number"
                        min="1"
                        value={task.duration}
                        onChange={e => updateTaskDuration(idx, e.target.value)}
                        style={{
                          width: 80,
                          padding: 6,
                          borderRadius: 4,
                          border: '1px solid #ccc'
                        }}
                      />
                    </td>
                    <td style={{ padding: 8 }}>
                      <input
                        type="time"
                        value={task.time_slot}
                        onChange={e => updateTaskTimeSlot(idx, e.target.value)}
                        style={{
                          padding: 6,
                          borderRadius: 4,
                          border: '1px solid #ccc'
                        }}
                      />
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>

            <div style={{ display: 'flex', gap: 16, alignItems: 'center', marginBottom: 16 }}>
              <label style={{ fontSize: 14 }}>
                Available from:
                <input
                  type="time"
                  value={timeWindowStart}
                  onChange={e => setTimeWindowStart(e.target.value)}
                  style={{ marginLeft: 8, padding: 6, borderRadius: 4, border: '1px solid #ccc' }}
                />
              </label>
              <label style={{ fontSize: 14 }}>
                to:
                <input
                  type="time"
                  value={timeWindowEnd}
                  onChange={e => setTimeWindowEnd(e.target.value)}
                  style={{ marginLeft: 8, padding: 6, borderRadius: 4, border: '1px solid #ccc' }}
                />
              </label>
            </div>

            <button
              onClick={submitConstraints}
              style={{
                padding: '10px 24px',
                borderRadius: 8,
                background: '#007bff',
                color: '#fff',
                border: 'none',
                cursor: 'pointer',
                fontSize: 14,
                fontWeight: 500,
              }}
            >
              Continue
            </button>
          </div>
        )}
      </div>

      {/* Constraint selection buttons */}
      {phase === 'constraint_clarification' && constraintOptions.length > 0 && !loading && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8, fontSize: 14, color: '#333' }}>
            Select an optimization preference:
          </div>
          <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
            {constraintOptions.map(option => (
              <button
                key={option.id}
                onClick={() => handleConstraintSelect(option)}
                style={{
                  padding: '12px 20px',
                  borderRadius: 8,
                  background: '#fff',
                  border: '2px solid #007bff',
                  color: '#007bff',
                  cursor: 'pointer',
                  fontSize: 14,
                  fontWeight: 500,
                  transition: 'all 0.2s',
                }}
                onMouseEnter={e => {
                  e.currentTarget.style.background = '#007bff'
                  e.currentTarget.style.color = '#fff'
                }}
                onMouseLeave={e => {
                  e.currentTarget.style.background = '#fff'
                  e.currentTarget.style.color = '#007bff'
                }}
                title={option.description}
              >
                {option.label}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Text input - hide during constraints phase */}
      {phase !== 'constraints' && (
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && send()}
            placeholder="Type your message..."
            style={{ flex: 1, padding: 12, borderRadius: 8, border: '1px solid #ccc' }}
          />
          <button
            onClick={() => send()}
            disabled={loading || !sessionId}
            style={{
              padding: '12px 24px',
              borderRadius: 8,
              background: loading ? '#ccc' : '#007bff',
              color: '#fff',
              border: 'none',
              cursor: loading ? 'default' : 'pointer'
            }}
          >
            Send
          </button>
        </div>
      )}
    </div>
  )
}
