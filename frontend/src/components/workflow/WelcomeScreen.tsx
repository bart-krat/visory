type WelcomeScreenProps = {
  loading: boolean
  sessionId: string | null
  onStartQuestionnaire: () => void
  onStartPlanning: () => void
}

export default function WelcomeScreen({
  loading,
  sessionId,
  onStartQuestionnaire,
  onStartPlanning,
}: WelcomeScreenProps) {
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
          onClick={onStartQuestionnaire}
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
          onClick={onStartPlanning}
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
