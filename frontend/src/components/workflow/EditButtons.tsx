type EditButtonsProps = {
  phase: string
  loading: boolean
  onNavigate: (targetPhase: string) => void
}

export default function EditButtons({ phase, loading, onNavigate }: EditButtonsProps) {
  // Show container starting from task collection phase
  if (!['collect_tasks', 'constraints', 'constraint_clarification', 'optimize', 'complete'].includes(phase)) {
    return null
  }

  // Check if any buttons should be shown
  const hasAnyButtons = ['constraints', 'constraint_clarification', 'optimize', 'complete'].includes(phase)

  return (
    <div style={{
      padding: hasAnyButtons ? 12 : 0,
      background: hasAnyButtons ? '#f8f9fa' : 'transparent',
      borderRadius: 8,
      border: hasAnyButtons ? '1px solid #dee2e6' : 'none',
      minHeight: hasAnyButtons ? 'auto' : 0,
      marginBottom: hasAnyButtons ? 16 : 0,
    }}>
      {hasAnyButtons && (
        <>
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
          </div>
        </>
      )}
    </div>
  )
}
