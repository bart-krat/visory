type EditButtonsProps = {
  phase: string
  loading: boolean
  onNavigate: (targetPhase: string) => void
}

export default function EditButtons({ phase, loading, onNavigate }: EditButtonsProps) {
  // Only show edit buttons after completing at least one phase
  if (!['constraints', 'constraint_clarification', 'optimize', 'complete'].includes(phase)) {
    return null
  }

  return (
    <div style={{
      marginBottom: 16,
      padding: 12,
      background: '#f8f9fa',
      borderRadius: 8,
      border: '1px solid #dee2e6',
    }}>
      <div style={{ fontSize: 13, color: '#666', marginBottom: 8 }}>
        Need to make changes?
      </div>
      <div style={{ display: 'flex', gap: 8, flexWrap: 'wrap' }}>
        {['constraints', 'constraint_clarification', 'optimize', 'complete'].includes(phase) && (
          <button
            onClick={() => onNavigate('collect_tasks')}
            disabled={loading}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              background: '#fff',
              border: '1px solid #007bff',
              color: '#007bff',
              cursor: loading ? 'default' : 'pointer',
              fontSize: 12,
            }}
          >
            ✏️ Edit Tasks
          </button>
        )}

        {['constraint_clarification', 'optimize', 'complete'].includes(phase) && (
          <button
            onClick={() => onNavigate('constraints')}
            disabled={loading}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              background: '#fff',
              border: '1px solid #007bff',
              color: '#007bff',
              cursor: loading ? 'default' : 'pointer',
              fontSize: 12,
            }}
          >
            ⏱️ Edit Durations & Times
          </button>
        )}

        {['optimize', 'complete'].includes(phase) && (
          <button
            onClick={() => onNavigate('constraint_clarification')}
            disabled={loading}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              background: '#fff',
              border: '1px solid #007bff',
              color: '#007bff',
              cursor: loading ? 'default' : 'pointer',
              fontSize: 12,
            }}
          >
            🎯 Edit Constraints
          </button>
        )}

        {phase === 'complete' && (
          <button
            onClick={() => onNavigate('reoptimize')}
            disabled={loading}
            style={{
              padding: '6px 12px',
              borderRadius: 6,
              background: '#28a745',
              border: 'none',
              color: '#fff',
              cursor: loading ? 'default' : 'pointer',
              fontSize: 12,
              fontWeight: 500,
            }}
          >
            🔄 Re-optimize
          </button>
        )}
      </div>
    </div>
  )
}
