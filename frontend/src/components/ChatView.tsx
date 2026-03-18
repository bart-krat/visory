import { useState, useEffect } from 'react'
import ScheduleView from './ScheduleView'

type Message = { role: 'user' | 'assistant'; content: string }
type ScheduledTask = {
  task: string
  category: string
  start_time: string
  end_time: string
  duration_minutes: number
}
type ConstraintOption = { id: string; label: string; description: string }
type ConstraintOptionsResponse = { options: ConstraintOption[]; supports_custom_text: boolean }
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
  const [selectedConstraints, setSelectedConstraints] = useState<Set<string>>(new Set())
  const [supportsCustomText, setSupportsCustomText] = useState(false)
  const [customConstraints, setCustomConstraints] = useState<string[]>([''])

  // Questionnaire progress
  const [questionnaireProgress, setQuestionnaireProgress] = useState<{current: number, total: number} | null>(null)

  // Constraints table state
  const [tasksForConstraints, setTasksForConstraints] = useState<TaskForConstraints[]>([])
  const [timeWindowStart, setTimeWindowStart] = useState('09:00')
  const [timeWindowEnd, setTimeWindowEnd] = useState('17:00')

  // Final schedule state
  const [finalSchedule, setFinalSchedule] = useState<ScheduledTask[] | null>(null)
  const [finalTimeWindow, setFinalTimeWindow] = useState<{ start_time: string; end_time: string } | null>(null)

  // Create session on mount (starts in welcome phase)
  useEffect(() => {
    const createSession = async () => {
      try {
        const res = await fetch('/api/workflow/start', { method: 'POST' })
        const data = await res.json()
        setSessionId(data.session_id)
        setPhase(data.phase)
        // Don't show welcome message in chat - we'll show buttons instead
      } catch {
        setMessages([{ role: 'assistant', content: 'Error starting. Is the server running?' }])
      }
    }
    createSession()
  }, [])

  // Start utility questionnaire
  const startQuestionnaire = async () => {
    if (!sessionId) return
    setLoading(true)
    try {
      const res = await fetch(`/api/utility/start?session_id=${sessionId}`, { method: 'POST' })
      const data = await res.json()
      setPhase(data.phase)
      setQuestionnaireProgress(data.progress)
      setMessages([{ role: 'assistant', content: data.message }])
    } catch {
      setMessages([{ role: 'assistant', content: 'Error starting questionnaire' }])
    }
    setLoading(false)
  }

  // Start planning directly
  const startPlanning = async () => {
    if (!sessionId) return
    setLoading(true)
    try {
      const res = await fetch(`/api/planning/start?session_id=${sessionId}`, { method: 'POST' })
      const data = await res.json()
      setPhase(data.phase)
      setMessages([{ role: 'assistant', content: data.message }])
    } catch {
      setMessages([{ role: 'assistant', content: 'Error starting planning' }])
    }
    setLoading(false)
  }

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
    if (phase === 'constraint_clarification' && sessionId) {
      const fetchOptions = async () => {
        try {
          const res = await fetch(`/api/constraints/options/${sessionId}`)
          const data: ConstraintOptionsResponse = await res.json()
          setConstraintOptions(data.options || [])
          setSupportsCustomText(data.supports_custom_text || false)
          setSelectedConstraints(new Set())
          setCustomConstraints([''])
        } catch {
          console.error('Failed to fetch constraint options')
        }
      }
      fetchOptions()
    } else {
      setConstraintOptions([])
      setSupportsCustomText(false)
      setSelectedConstraints(new Set())
      setCustomConstraints([''])
    }
  }, [phase, sessionId])

  // Fetch final schedule when complete
  useEffect(() => {
    if (phase === 'complete' && sessionId) {
      const fetchSchedule = async () => {
        try {
          const res = await fetch(`/api/workflow/${sessionId}/state`)
          const data = await res.json()
          if (data.daily_plan?.schedule) {
            setFinalSchedule(data.daily_plan.schedule)
            setFinalTimeWindow(data.daily_plan.time_window || data.time_window)
          }
        } catch {
          console.error('Failed to fetch schedule')
        }
      }
      fetchSchedule()
    }
  }, [phase, sessionId])

  // Fetch current phase from server
  const fetchCurrentPhase = async () => {
    if (!sessionId) return
    try {
      const res = await fetch(`/api/workflow/${sessionId}/state`)
      const data = await res.json()
      setPhase(data.phase)
      if (data.questionnaire_progress) {
        setQuestionnaireProgress(data.questionnaire_progress)
      }
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
      // Use utility endpoint for questionnaire, workflow endpoint for other phases
      if (phase === 'questionnaire') {
        const res = await fetch('/api/utility/message', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId, message: msgToSend })
        })
        const data = await res.json()

        setMessages(prev => [...prev, { role: 'assistant', content: data.message }])
        setPhase(data.phase)

        if (data.progress) {
          setQuestionnaireProgress(data.progress)
        }

        // If questionnaire complete, show option to start planning
        if (data.is_complete) {
          setQuestionnaireProgress(null)
        }
      } else {
        // Use streaming workflow endpoint for other phases
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
      }
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error connecting to server' }])
    }
    setLoading(false)
  }

  const toggleConstraint = (optionId: string) => {
    // Clear custom constraints when selecting buttons
    if (customConstraints.some(c => c.trim())) {
      setCustomConstraints([''])
    }
    setSelectedConstraints(prev => {
      const newSet = new Set(prev)
      if (newSet.has(optionId)) {
        newSet.delete(optionId)
      } else {
        newSet.add(optionId)
      }
      return newSet
    })
  }

  const submitConstraints2 = async () => {
    if (!sessionId) return

    const constraintIds = Array.from(selectedConstraints)
    // Filter out empty constraints and join with semicolon
    const validConstraints = customConstraints.filter(c => c.trim().length > 0)
    const combinedConstraintText = validConstraints.join('; ')
    const hasCustomText = validConstraints.length > 0
    const hasButtonSelection = constraintIds.length > 0

    // Need at least one constraint type
    if (!hasCustomText && !hasButtonSelection) {
      // No constraints - will optimize for max utility
    }

    setLoading(true)

    try {
      const res = await fetch('/api/constraints/submit', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          session_id: sessionId,
          constraint_ids: constraintIds,
          custom_constraint: hasCustomText ? combinedConstraintText : null,
        })
      })

      const data = await res.json()

      // Show what the user selected
      let userMessage = ''
      if (hasCustomText) {
        if (validConstraints.length === 1) {
          userMessage = `Constraint: "${validConstraints[0].trim()}"`
        } else {
          userMessage = `Constraints:\n${validConstraints.map(c => `  - ${c.trim()}`).join('\n')}`
        }
      } else if (hasButtonSelection) {
        const constraintLabels = constraintOptions
          .filter(opt => selectedConstraints.has(opt.id))
          .map(opt => opt.label)
          .join(', ')
        userMessage = `Constraints: ${constraintLabels}`
      } else {
        userMessage = 'Optimize schedule'
      }

      setMessages(prev => [
        ...prev,
        { role: 'user', content: userMessage },
        { role: 'assistant', content: data.message }
      ])

      setPhase(data.phase)
      setSelectedConstraints(new Set())
      setConstraintOptions([])
      setCustomConstraints([''])

    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error running optimization' }])
    }

    setLoading(false)
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
    return { health: '💪', work: '💼', personal: '🎮' }[category] || '📌'
  }

  const getPhaseLabel = () => {
    const labels: Record<string, string> = {
      'welcome': 'Welcome',
      'questionnaire': 'Values Assessment',
      'evaluation_complete': 'Assessment Complete',
      'collect_tasks': 'Task Collection',
      'constraints': 'Time Constraints',
      'constraint_clarification': 'Optimization Preferences',
      'optimize': 'Optimizing...',
      'complete': 'Complete',
    }
    return labels[phase] || phase
  }

  // Welcome screen
  if (phase === 'welcome') {
    return (
      <div style={{ padding: '20px 0' }}>
        <div style={{ textAlign: 'center', marginBottom: 32 }}>
          <div style={{
            width: 64,
            height: 64,
            borderRadius: 16,
            background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            margin: '0 auto 16px auto',
            fontSize: 28,
            boxShadow: '0 4px 15px rgba(102, 126, 234, 0.4)',
          }}>
            ✨
          </div>
          <h2 style={{ margin: '0 0 8px 0', fontSize: 22, fontWeight: 600, color: '#333' }}>
            How would you like to start?
          </h2>
          <p style={{ color: '#666', margin: 0, fontSize: 14 }}>
            Choose an option below to begin
          </p>
        </div>

        <div style={{
          display: 'flex',
          flexDirection: 'column',
          gap: 12,
        }}>
          {/* Questionnaire Option */}
          <button
            onClick={startQuestionnaire}
            disabled={loading || !sessionId}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              padding: '20px',
              borderRadius: 16,
              background: 'linear-gradient(135deg, #667eea 0%, #764ba2 100%)',
              color: '#fff',
              border: 'none',
              cursor: loading ? 'default' : 'pointer',
              textAlign: 'left',
              transition: 'transform 0.2s, box-shadow 0.2s',
              boxShadow: '0 4px 15px rgba(102, 126, 234, 0.3)',
            }}
          >
            <div style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: 'rgba(255, 255, 255, 0.2)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 24,
              flexShrink: 0,
            }}>
              🧠
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>
                Let AI Get to Know You
              </div>
              <div style={{ fontSize: 13, opacity: 0.9 }}>
                Answer questions to personalize your planning
              </div>
            </div>
            <div style={{ fontSize: 20, opacity: 0.7 }}>→</div>
          </button>

          {/* Plan Option */}
          <button
            onClick={startPlanning}
            disabled={loading || !sessionId}
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: 16,
              padding: '20px',
              borderRadius: 16,
              background: '#fff',
              color: '#333',
              border: '2px solid #e8e8e8',
              cursor: loading ? 'default' : 'pointer',
              textAlign: 'left',
              transition: 'transform 0.2s, border-color 0.2s',
            }}
          >
            <div style={{
              width: 48,
              height: 48,
              borderRadius: 12,
              background: '#f5f5f5',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: 24,
              flexShrink: 0,
            }}>
              ⚡
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontSize: 16, fontWeight: 600, marginBottom: 4 }}>
                Plan Your Day
              </div>
              <div style={{ fontSize: 13, color: '#666' }}>
                Jump straight into task planning
              </div>
            </div>
            <div style={{ fontSize: 20, color: '#ccc' }}>→</div>
          </button>
        </div>

        {loading && (
          <div style={{
            marginTop: 24,
            textAlign: 'center',
            color: '#666',
            fontSize: 14,
          }}>
            Loading...
          </div>
        )}
      </div>
    )
  }

  const showScheduleSideBySide = phase === 'complete' && finalSchedule && finalTimeWindow

  return (
    <div style={{
      display: 'flex',
      gap: 24,
      alignItems: 'stretch',
      height: showScheduleSideBySide ? 'calc(100vh - 220px)' : 'auto',
    }}>
      {/* Chat Column */}
      <div style={{
        flex: 1,
        minWidth: 0,
        overflowY: 'auto',
        maxHeight: showScheduleSideBySide ? '100%' : 'none',
      }}>
        {phase && phase !== 'complete' && (
          <div style={{ marginBottom: 12 }}>
            <div style={{ fontSize: 12, color: '#666', marginBottom: 4 }}>
              Phase: {getPhaseLabel()}
            </div>
          {/* Questionnaire progress bar */}
          {phase === 'questionnaire' && questionnaireProgress && (
            <div style={{ marginTop: 4 }}>
              <div style={{
                height: 6,
                background: '#e9ecef',
                borderRadius: 3,
                overflow: 'hidden',
              }}>
                <div style={{
                  height: '100%',
                  width: `${(questionnaireProgress.current / questionnaireProgress.total) * 100}%`,
                  background: '#007bff',
                  transition: 'width 0.3s ease',
                }} />
              </div>
              <div style={{ fontSize: 11, color: '#888', marginTop: 2 }}>
                Question {questionnaireProgress.current} of {questionnaireProgress.total}
              </div>
            </div>
          )}
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

      {/* Constraint selection UI */}
      {phase === 'constraint_clarification' && !loading && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 12, fontSize: 14, color: '#333' }}>
            Add additional constraints (optional):
          </div>

          {/* Custom text inputs */}
          {supportsCustomText && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
                Describe your requirements in your own words:
              </div>
              {customConstraints.map((constraint, index) => (
                <div key={index} style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
                  <input
                    type="text"
                    value={constraint}
                    onChange={e => {
                      const newConstraints = [...customConstraints]
                      newConstraints[index] = e.target.value
                      setCustomConstraints(newConstraints)
                      // Clear button selections when typing custom text
                      if (e.target.value.trim() && selectedConstraints.size > 0) {
                        setSelectedConstraints(new Set())
                      }
                    }}
                    placeholder={index === 0
                      ? 'e.g., "gym before lunch" or "must include meeting"'
                      : 'Add another constraint...'
                    }
                    style={{
                      flex: 1,
                      padding: 12,
                      borderRadius: 8,
                      border: '1px solid #ccc',
                      fontSize: 14,
                      boxSizing: 'border-box',
                    }}
                  />
                  {/* Remove button (show if more than one constraint) */}
                  {customConstraints.length > 1 && (
                    <button
                      onClick={() => {
                        const newConstraints = customConstraints.filter((_, i) => i !== index)
                        setCustomConstraints(newConstraints)
                      }}
                      style={{
                        width: 40,
                        height: 40,
                        borderRadius: 8,
                        border: '1px solid #dc3545',
                        background: '#fff',
                        color: '#dc3545',
                        cursor: 'pointer',
                        fontSize: 18,
                        fontWeight: 'bold',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                      title="Remove constraint"
                    >
                      -
                    </button>
                  )}
                  {/* Add button (show only on last row) */}
                  {index === customConstraints.length - 1 && (
                    <button
                      onClick={() => setCustomConstraints([...customConstraints, ''])}
                      style={{
                        width: 40,
                        height: 40,
                        borderRadius: 8,
                        border: '1px solid #28a745',
                        background: '#fff',
                        color: '#28a745',
                        cursor: 'pointer',
                        fontSize: 18,
                        fontWeight: 'bold',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                      }}
                      title="Add another constraint"
                    >
                      +
                    </button>
                  )}
                </div>
              ))}
              <div style={{ fontSize: 11, color: '#888', marginTop: 4 }}>
                {customConstraints.filter(c => c.trim()).length > 0
                  ? `${customConstraints.filter(c => c.trim()).length} constraint${customConstraints.filter(c => c.trim()).length > 1 ? 's' : ''} entered`
                  : 'Click + to add multiple constraints'
                }
              </div>
            </div>
          )}

          {/* Task buttons */}
          {constraintOptions.length > 0 && (
            <div style={{ marginBottom: 16 }}>
              <div style={{ fontSize: 12, color: '#666', marginBottom: 6 }}>
                Or select specific tasks that must be included:
              </div>
              <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                {constraintOptions.map(option => {
                  const isSelected = selectedConstraints.has(option.id)
                  return (
                    <button
                      key={option.id}
                      onClick={() => toggleConstraint(option.id)}
                      style={{
                        padding: '8px 14px',
                        borderRadius: 8,
                        background: isSelected ? '#6c757d' : '#fff',
                        border: '2px solid #6c757d',
                        color: isSelected ? '#fff' : '#6c757d',
                        cursor: 'pointer',
                        fontSize: 13,
                        fontWeight: 500,
                        transition: 'all 0.2s',
                      }}
                      title={option.description}
                    >
                      {isSelected && '✓ '}{option.label}
                    </button>
                  )
                })}
              </div>
            </div>
          )}

          {/* Optimize button */}
          <div style={{ marginTop: 16 }}>
            <button
              onClick={submitConstraints2}
              style={{
                padding: '12px 28px',
                borderRadius: 8,
                background: '#007bff',
                color: '#fff',
                border: 'none',
                cursor: 'pointer',
                fontSize: 14,
                fontWeight: 600,
              }}
            >
              Optimize
            </button>
            <span style={{ marginLeft: 12, fontSize: 13, color: '#666' }}>
              {customConstraints.some(c => c.trim())
                ? `${customConstraints.filter(c => c.trim()).length} custom constraint${customConstraints.filter(c => c.trim()).length > 1 ? 's' : ''}`
                : selectedConstraints.size > 0
                  ? `${selectedConstraints.size} task${selectedConstraints.size > 1 ? 's' : ''} must be included`
                  : 'Fixed times from above will be applied'
              }
            </span>
          </div>
        </div>
      )}

      {/* Start Planning button after questionnaire complete */}
      {phase === 'evaluation_complete' && (
        <div style={{ textAlign: 'center', marginBottom: 16 }}>
          <button
            onClick={startPlanning}
            disabled={loading}
            style={{
              padding: '14px 32px',
              borderRadius: 8,
              background: '#007bff',
              color: '#fff',
              border: 'none',
              cursor: loading ? 'default' : 'pointer',
              fontSize: 16,
              fontWeight: 500,
            }}
          >
            Plan Your Day
          </button>
        </div>
      )}

      {/* Text input - show during questionnaire and collect_tasks phases */}
      {['questionnaire', 'collect_tasks'].includes(phase) && (
        <div style={{ display: 'flex', gap: 8 }}>
          <input
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => e.key === 'Enter' && !loading && send()}
            placeholder={phase === 'questionnaire' ? "Type your answer..." : "Type your tasks..."}
            style={{ flex: 1, padding: 12, borderRadius: 8, border: '1px solid #ccc' }}
            disabled={loading}
          />
          <button
            onClick={() => send()}
            disabled={loading || !sessionId || !input.trim()}
            style={{
              padding: '12px 24px',
              borderRadius: 8,
              background: loading || !input.trim() ? '#ccc' : '#007bff',
              color: '#fff',
              border: 'none',
              cursor: loading || !input.trim() ? 'default' : 'pointer'
            }}
          >
            {loading ? '...' : 'Send'}
          </button>
        </div>
      )}

      {/* Completion message */}
      {phase === 'complete' && (
        <div style={{
          textAlign: 'center',
          padding: '40px 20px',
          color: '#666',
        }}>
          <div style={{ fontSize: 48, marginBottom: 16 }}>✅</div>
          <div style={{ fontSize: 18, fontWeight: 600, color: '#333', marginBottom: 8 }}>
            Your day is planned!
          </div>
          <div style={{ fontSize: 14 }}>
            Check out your optimized schedule →
          </div>
        </div>
      )}
      </div>

      {/* Schedule Column - shown when complete */}
      {showScheduleSideBySide && (
        <div style={{
          flex: 1,
          minWidth: 0,
          overflowY: 'auto',
          maxHeight: '100%',
        }}>
          <ScheduleView schedule={finalSchedule} timeWindow={finalTimeWindow} />
        </div>
      )}
    </div>
  )
}
