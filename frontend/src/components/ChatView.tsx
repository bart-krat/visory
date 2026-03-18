import { useState, useEffect } from 'react'

type Message = { role: 'user' | 'assistant'; content: string }
type ConstraintOption = { id: string; label: string; description: string }

export default function ChatView() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [phase, setPhase] = useState<string>('')
  const [constraintOptions, setConstraintOptions] = useState<ConstraintOption[]>([])

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

      // Handle streaming response
      const reader = res.body?.getReader()
      if (!reader) throw new Error('No reader')

      const decoder = new TextDecoder()
      let assistantContent = ''

      // Add empty assistant message that we'll update
      setMessages(prev => [...prev, { role: 'assistant', content: '' }])

      while (true) {
        const { done, value } = await reader.read()
        if (done) break

        const chunk = decoder.decode(value)
        assistantContent += chunk

        // Update the last message with streamed content
        setMessages(prev => {
          const updated = [...prev]
          updated[updated.length - 1] = { role: 'assistant', content: assistantContent }
          return updated
        })
      }

      // Fetch the current phase AFTER streaming completes
      // (header is set before generator runs, so it's stale)
      await fetchCurrentPhase()

    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error connecting to server' }])
    }
    setLoading(false)
  }

  const handleConstraintSelect = (option: ConstraintOption) => {
    send(option.id)
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
      </div>

      {/* Constraint selection buttons */}
      {phase === 'constraint_clarification' && constraintOptions.length > 0 && !loading && (
        <div style={{ marginBottom: 16 }}>
          <div style={{ marginBottom: 8, fontSize: 14, color: '#333' }}>
            Select an option:
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
    </div>
  )
}
