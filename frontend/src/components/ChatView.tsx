import { useState, useEffect } from 'react'

type Message = { role: 'user' | 'assistant'; content: string }

export default function ChatView() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sessionId, setSessionId] = useState<string | null>(null)
  const [phase, setPhase] = useState<string>('')

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

  const send = async () => {
    if (!input.trim() || !sessionId) return

    const userMsg: Message = { role: 'user', content: input }
    setMessages(prev => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await fetch('/api/workflow/message', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ session_id: sessionId, message: input })
      })

      // Update phase from header if present
      const newPhase = res.headers.get('X-Workflow-Phase')
      if (newPhase) setPhase(newPhase)

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
    } catch {
      setMessages(prev => [...prev, { role: 'assistant', content: 'Error connecting to server' }])
    }
    setLoading(false)
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
      <div style={{ display: 'flex', gap: 8 }}>
        <input
          value={input}
          onChange={e => setInput(e.target.value)}
          onKeyDown={e => e.key === 'Enter' && send()}
          placeholder="Enter your tasks..."
          style={{ flex: 1, padding: 12, borderRadius: 8, border: '1px solid #ccc' }}
        />
        <button
          onClick={send}
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
