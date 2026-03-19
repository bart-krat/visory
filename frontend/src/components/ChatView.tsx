import { useState, useEffect } from 'react'
import ScheduleView from './ScheduleView'
import WelcomeScreen from './workflow/WelcomeScreen'
import EditButtons from './workflow/EditButtons'
import { useWorkflowAPI } from '../hooks/useWorkflowAPI'
import { categoryEmojis, phaseLabels } from '../styles/constants'

type Message = { role: 'user' | 'assistant'; content: string }
type ScheduledTask = {
  task: string
  category: string
  start_time: string
  end_time: string
  duration_minutes: number
}
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
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [phase, setPhase] = useState<string>('')

  // Use workflow API hook
  const api = useWorkflowAPI(sessionId)
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
    const data = await api.startQuestionnaire()
    if (data) {
      if (data.error) {
        setMessages([{ role: 'assistant', content: data.error }])
      } else {
        setPhase(data.phase)
        setQuestionnaireProgress(data.progress)
        setMessages([{ role: 'assistant', content: data.message }])
      }
    }
  }

  // Start planning directly
  const startPlanning = async () => {
    const data = await api.startPlanning()
    if (data) {
      if (data.error) {
        setMessages([{ role: 'assistant', content: data.error }])
      } else {
        setPhase(data.phase)
        setMessages([{ role: 'assistant', content: data.message }])
      }
    }
  }

  // Fetch tasks when entering constraints phase
  useEffect(() => {
    if (phase === 'constraints' && sessionId) {
      const fetchTasks = async () => {
        const data = await api.fetchWorkflowState()
        if (data?.tasks) {
          // Pre-populate tasks with existing durations and time slots
          setTasksForConstraints(
            data.tasks.map((t: any) => {
              // Convert time_slot from minutes to "HH:MM" format
              let timeSlot = ''
              if (t.time_slot !== null && t.time_slot !== undefined) {
                const hours = Math.floor(t.time_slot / 60)
                const minutes = t.time_slot % 60
                timeSlot = `${String(hours).padStart(2, '0')}:${String(minutes).padStart(2, '0')}`
              }
              return {
                name: t.name,
                category: t.category,
                duration: t.duration || 30,
                time_slot: timeSlot,
              }
            })
          )
        }

        // Pre-populate time window if it exists
        if (data?.time_window) {
          setTimeWindowStart(data.time_window.start_time)
          setTimeWindowEnd(data.time_window.end_time)
        }
      }
      fetchTasks()
    }
  }, [phase, sessionId])

  // Fetch constraint options when entering constraint_clarification phase
  useEffect(() => {
    if (phase === 'constraint_clarification' && sessionId) {
      const fetchOptions = async () => {
        // Fetch available constraint options
        const optionsData = await api.fetchConstraintOptions()
        if (optionsData) {
          setConstraintOptions(optionsData.options || [])
          setSupportsCustomText(optionsData.supports_custom_text || false)
        }

        // Fetch current state to pre-populate existing selections
        const stateData = await api.fetchWorkflowState()
        if (stateData?.constraints) {
          // Map mandatory_tasks to button IDs (format: TASK_{task_name})
          const preSelectedConstraints = new Set<string>()

          if (stateData.constraints.mandatory_tasks) {
            stateData.constraints.mandatory_tasks.forEach((taskName: string) => {
              preSelectedConstraints.add(`TASK_${taskName}`)
            })
          }

          setSelectedConstraints(preSelectedConstraints)

          // Extract custom text constraints from "undefined" constraint types
          const customTextConstraints: string[] = []
          if (stateData.constraints.raw && Array.isArray(stateData.constraints.raw)) {
            stateData.constraints.raw.forEach((constraint: any) => {
              if (constraint.type === 'undefined' && constraint.description) {
                customTextConstraints.push(constraint.description)
              }
            })
          }

          // Pre-populate custom constraints text boxes
          if (customTextConstraints.length > 0) {
            setCustomConstraints(customTextConstraints)
          } else if (preSelectedConstraints.size === 0) {
            // Only reset to empty if no button or custom constraints exist
            setCustomConstraints([''])
          }
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
        const data = await api.fetchWorkflowState()
        if (data?.daily_plan?.schedule) {
          setFinalSchedule(data.daily_plan.schedule)
          setFinalTimeWindow(data.daily_plan.time_window || data.time_window)
        }
      }
      fetchSchedule()
    }
  }, [phase, sessionId])

  // Fetch current phase from server
  const fetchCurrentPhase = async () => {
    const data = await api.fetchWorkflowState()
    if (data) {
      setPhase(data.phase)
      if (data.questionnaire_progress) {
        setQuestionnaireProgress(data.questionnaire_progress)
      }
    }
  }

  // Navigate to a specific phase
  const navigateToPhase = async (targetPhase: string) => {
    const data = await api.navigateToPhase(targetPhase)
    if (data) {
      if (data.error) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.error }])
      } else {
        // Clear chat history when returning to questionnaire for a fresh start
        if (targetPhase === 'questionnaire') {
          setMessages([{ role: 'assistant', content: data.message }])
        } else {
          setMessages(prev => [
            ...prev,
            { role: 'assistant', content: data.message }
          ])
        }
        setPhase(data.phase)

        // Handle questionnaire progress if returning to questionnaire
        if (data.progress) {
          setQuestionnaireProgress(data.progress)
        }
      }
    }
  }

  const send = async (message?: string) => {
    const msgToSend = message ?? input
    if (!msgToSend.trim() || !sessionId) return

    const userMsg: Message = { role: 'user', content: msgToSend }
    setMessages(prev => [...prev, userMsg])
    setInput('')

    const result = await api.sendMessage(msgToSend, phase)

    if (result) {
      if (result.error) {
        setMessages(prev => [...prev, { role: 'assistant', content: result.error }])
      } else if (result.type === 'json' && result.data) {
        // Questionnaire response
        setMessages(prev => [...prev, { role: 'assistant', content: result.data.message }])
        setPhase(result.data.phase)

        if (result.data.progress) {
          setQuestionnaireProgress(result.data.progress)
        }

        if (result.data.is_complete) {
          setQuestionnaireProgress(null)
        }
      } else if (result.type === 'stream' && result.response) {
        // Streaming response
        const reader = result.response.body?.getReader()
        if (!reader) {
          setMessages(prev => [...prev, { role: 'assistant', content: 'Error reading stream' }])
          return
        }

        const decoder = new TextDecoder()
        let assistantContent = ''

        setMessages(prev => [...prev, { role: 'assistant', content: '' }])

        while (true) {
          const { done, value } = await reader.read()
          if (done) break

          const chunk = decoder.decode(value)
          assistantContent += chunk

          setMessages(prev => {
            if (prev.length === 0) return prev
            const updated = [...prev]
            updated[updated.length - 1] = { role: 'assistant', content: assistantContent }
            return updated
          })
        }

        api.setLoading(false)
        await fetchCurrentPhase()
      }
    }
  }

  const toggleConstraint = (optionId: string) => {
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

  const submitOptimizationConstraints = async () => {
    const constraintIds = Array.from(selectedConstraints)
    const validConstraints = customConstraints.filter(c => c.trim().length > 0)
    const combinedConstraintText = validConstraints.join('; ')
    const hasCustomText = validConstraints.length > 0
    const hasButtonSelection = constraintIds.length > 0

    const data = await api.submitOptimizationConstraints(
      constraintIds,
      hasCustomText ? combinedConstraintText : null
    )

    if (data) {
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

      if (data.error) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.error }])
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'user', content: userMessage },
          { role: 'assistant', content: data.message }
        ])
        setPhase(data.phase)
      }

      setSelectedConstraints(new Set())
      setConstraintOptions([])
      setCustomConstraints([''])
    }
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

  const submitTaskDurationsAndTimes = async () => {
    // Validate all durations are set
    const invalidTasks = tasksForConstraints.filter(t => !t.duration || t.duration <= 0)
    if (invalidTasks.length > 0) {
      alert('Please set a duration for all tasks')
      return
    }

    const tasks = tasksForConstraints.map(t => ({
      name: t.name,
      duration: t.duration,
      time_slot: t.time_slot || null,
    }))

    const data = await api.submitTaskDurationsAndTimes(tasks, timeWindowStart, timeWindowEnd)

    if (data) {
      // Add a summary message
      const summary = tasksForConstraints
        .map(t => `${t.name}: ${t.duration} min${t.time_slot ? ` @ ${t.time_slot}` : ''}`)
        .join('\n')

      if (data.error) {
        setMessages(prev => [...prev, { role: 'assistant', content: data.error }])
      } else {
        setMessages(prev => [
          ...prev,
          { role: 'user', content: `Time window: ${timeWindowStart} - ${timeWindowEnd}\n\n${summary}` },
          { role: 'assistant', content: data.message }
        ])
        setPhase(data.phase)
      }

      setTasksForConstraints([])
    }
  }

  const getCategoryEmoji = (category: string) => {
    return categoryEmojis[category] || '📌'
  }

  const getPhaseLabel = () => {
    return phaseLabels[phase] || phase
  }

  const handleSaveSchedule = async () => {
    if (!finalSchedule || !sessionId) return

    // TODO: Implement save to calendar backend
    const today = new Date().toISOString().split('T')[0]
    console.log('Saving schedule for date:', today, finalSchedule)
    alert('Schedule save functionality coming soon!')
  }

  const handleViewCalendar = () => {
    // TODO: Navigate to calendar view
    alert('Calendar view coming soon!')
  }

  // Welcome screen
  if (phase === 'welcome') {
    return (
      <WelcomeScreen
        loading={api.loading}
        sessionId={sessionId}
        onStartQuestionnaire={startQuestionnaire}
        onStartPlanning={startPlanning}
      />
    )
  }

  const showScheduleSideBySide = phase === 'complete' && finalSchedule && finalTimeWindow

  return (
    <div style={{
      display: 'flex',
      flexDirection: 'column',
      height: showScheduleSideBySide ? 'calc(100vh - 220px)' : 'auto',
    }}>
      {/* Pinned Edit Buttons at Top */}
      <div style={{
        position: 'sticky',
        top: 0,
        zIndex: 10,
        background: '#fff',
        paddingBottom: 8,
      }}>
        <EditButtons phase={phase} loading={api.loading} onNavigate={navigateToPhase} />
      </div>

      {/* Main Content Area */}
      <div style={{
        display: 'flex',
        gap: 24,
        alignItems: 'stretch',
        flex: 1,
        minHeight: 0,
      }}>
        {/* Chat Column */}
        <div style={{
          flex: 1,
          minWidth: 0,
          overflowY: 'auto',
          maxHeight: '100%',
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
                    background: '#14b8a6',
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
              background: m.role === 'user' ? '#14b8a6' : '#e9ecef',
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
        {api.loading && <div style={{ color: '#666' }}>Thinking...</div>}

        {/* Constraints Table */}
        {phase === 'constraints' && tasksForConstraints.length > 0 && !api.loading && (
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
              onClick={submitTaskDurationsAndTimes}
              style={{
                padding: '10px 24px',
                borderRadius: 8,
                background: '#14b8a6',
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
      {phase === 'constraint_clarification' && !api.loading && (
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
              onClick={submitOptimizationConstraints}
              style={{
                padding: '12px 28px',
                borderRadius: 8,
                background: '#14b8a6',
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
            disabled={api.loading}
            style={{
              padding: '14px 32px',
              borderRadius: 8,
              background: '#14b8a6',
              color: '#fff',
              border: 'none',
              cursor: api.loading ? 'default' : 'pointer',
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
            onKeyDown={e => e.key === 'Enter' && !api.loading && send()}
            placeholder={phase === 'questionnaire' ? "Type your answer..." : "Type your tasks..."}
            style={{ flex: 1, padding: 12, borderRadius: 8, border: '1px solid #ccc' }}
            disabled={api.loading}
          />
          <button
            onClick={() => send()}
            disabled={api.loading || !sessionId || !input.trim()}
            style={{
              padding: '12px 24px',
              borderRadius: 8,
              background: api.loading || !input.trim() ? '#ccc' : '#14b8a6',
              color: '#fff',
              border: 'none',
              cursor: api.loading || !input.trim() ? 'default' : 'pointer'
            }}
          >
            {api.loading ? '...' : 'Send'}
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
            display: 'flex',
            flexDirection: 'column',
            maxHeight: '100%',
          }}>
            {/* Action buttons above schedule */}
            <div style={{
              display: 'flex',
              gap: 12,
              marginBottom: 16,
              padding: '0 4px',
            }}>
              <button
                onClick={handleSaveSchedule}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  borderRadius: 8,
                  background: '#28a745',
                  color: '#fff',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: 14,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                💾 Save Schedule
              </button>
              <button
                onClick={handleViewCalendar}
                style={{
                  flex: 1,
                  padding: '12px 20px',
                  borderRadius: 8,
                  background: '#14b8a6',
                  color: '#fff',
                  border: 'none',
                  cursor: 'pointer',
                  fontSize: 14,
                  fontWeight: 600,
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                }}
              >
                📅 View Calendar
              </button>
            </div>

            {/* Schedule view */}
            <div style={{
              flex: 1,
              overflowY: 'auto',
            }}>
              <ScheduleView schedule={finalSchedule} timeWindow={finalTimeWindow} />
            </div>
          </div>
        )}
      </div>
    </div>
  )
}
