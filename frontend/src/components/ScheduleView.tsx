type ScheduledTask = {
  task: string
  category: string
  start_time: string
  end_time: string
  duration_minutes: number
}

type ScheduleViewProps = {
  schedule: ScheduledTask[]
  timeWindow: { start_time: string; end_time: string }
  showFullDay?: boolean
}

const CATEGORY_COLORS: Record<string, { bg: string; border: string; text: string }> = {
  health: { bg: '#d4edda', border: '#28a745', text: '#155724' },
  work: { bg: '#cce5ff', border: '#007bff', text: '#004085' },
  personal: { bg: '#fff3cd', border: '#ffc107', text: '#856404' },
}

const CATEGORY_ICONS: Record<string, string> = {
  health: '💪',
  work: '💼',
  personal: '🎮',
}

function parseTime(timeStr: string): number {
  const [hours, minutes] = timeStr.split(':').map(Number)
  return hours * 60 + minutes
}

function formatHour(hour: number): string {
  const period = hour >= 12 ? 'PM' : 'AM'
  const displayHour = hour > 12 ? hour - 12 : hour === 0 ? 12 : hour
  return `${displayHour} ${period}`
}

function getDateString(): string {
  const now = new Date()
  const options: Intl.DateTimeFormatOptions = {
    weekday: 'long',
    year: 'numeric',
    month: 'long',
    day: 'numeric'
  }
  return now.toLocaleDateString('en-US', options)
}

export default function ScheduleView({ schedule, timeWindow, showFullDay = true }: ScheduleViewProps) {
  const windowStartMinutes = parseTime(timeWindow.start_time)
  const windowEndMinutes = parseTime(timeWindow.end_time)

  // Show full day from 6 AM to 11 PM, or use time window if showFullDay is false
  const startHour = showFullDay ? 6 : Math.floor(windowStartMinutes / 60)
  const endHour = showFullDay ? 23 : Math.ceil(windowEndMinutes / 60)
  const hours = Array.from({ length: endHour - startHour }, (_, i) => startHour + i)

  // Calculate start in minutes for positioning (based on display start, not time window)
  const displayStartMinutes = startHour * 60

  const HOUR_HEIGHT = 60 // pixels per hour
  const PIXELS_PER_MINUTE = HOUR_HEIGHT / 60

  return (
    <div style={{
      background: '#fff',
      borderRadius: 12,
      boxShadow: '0 2px 12px rgba(0,0,0,0.1)',
      overflow: 'hidden',
      marginTop: 16,
    }}>
      {/* Header with date */}
      <div style={{
        background: 'linear-gradient(135deg, #007bff 0%, #0056b3 100%)',
        color: '#fff',
        padding: '16px 20px',
      }}>
        <div style={{ fontSize: 13, opacity: 0.9, marginBottom: 4 }}>Your Schedule</div>
        <div style={{ fontSize: 18, fontWeight: 600 }}>{getDateString()}</div>
      </div>

      {/* Schedule grid */}
      <div style={{
        display: 'flex',
        padding: '16px 12px',
        background: '#fafafa',
      }}>
        {/* Time labels */}
        <div style={{
          width: 60,
          flexShrink: 0,
          position: 'relative',
        }}>
          {hours.map((hour) => (
            <div
              key={hour}
              style={{
                height: HOUR_HEIGHT,
                fontSize: 12,
                color: '#666',
                textAlign: 'right',
                paddingRight: 8,
                position: 'relative',
                top: -8,
              }}
            >
              {formatHour(hour)}
            </div>
          ))}
        </div>

        {/* Schedule blocks */}
        <div style={{
          flex: 1,
          position: 'relative',
          borderLeft: '1px solid #e0e0e0',
          minHeight: hours.length * HOUR_HEIGHT,
        }}>
          {/* Available time window highlight */}
          {showFullDay && (
            <div
              style={{
                position: 'absolute',
                top: (windowStartMinutes - displayStartMinutes) * PIXELS_PER_MINUTE,
                left: 0,
                right: 0,
                height: (windowEndMinutes - windowStartMinutes) * PIXELS_PER_MINUTE,
                background: 'rgba(0, 123, 255, 0.04)',
                borderTop: '2px dashed rgba(0, 123, 255, 0.3)',
                borderBottom: '2px dashed rgba(0, 123, 255, 0.3)',
                pointerEvents: 'none',
              }}
            />
          )}

          {/* Hour lines */}
          {hours.map((hour, idx) => (
            <div
              key={hour}
              style={{
                position: 'absolute',
                top: idx * HOUR_HEIGHT,
                left: 0,
                right: 0,
                borderTop: '1px solid #e9ecef',
                height: HOUR_HEIGHT,
              }}
            />
          ))}

          {/* Task blocks */}
          {schedule.map((task, idx) => {
            const taskStart = parseTime(task.start_time)
            const taskEnd = parseTime(task.end_time)
            const topOffset = (taskStart - displayStartMinutes) * PIXELS_PER_MINUTE
            const height = (taskEnd - taskStart) * PIXELS_PER_MINUTE
            const colors = CATEGORY_COLORS[task.category] || CATEGORY_COLORS.personal
            const icon = CATEGORY_ICONS[task.category] || '📌'

            return (
              <div
                key={idx}
                style={{
                  position: 'absolute',
                  top: topOffset,
                  left: 8,
                  right: 8,
                  height: height - 4,
                  background: colors.bg,
                  borderLeft: `4px solid ${colors.border}`,
                  borderRadius: 6,
                  padding: '8px 10px',
                  boxSizing: 'border-box',
                  overflow: 'hidden',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.1)',
                }}
              >
                <div style={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 8,
                  height: '100%',
                }}>
                  <span style={{ fontSize: 16 }}>{icon}</span>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{
                      fontWeight: 600,
                      fontSize: 14,
                      color: colors.text,
                      whiteSpace: 'nowrap',
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                    }}>
                      {task.task}
                    </div>
                    <div style={{
                      fontSize: 12,
                      color: colors.text,
                      opacity: 0.8,
                      marginTop: 2,
                    }}>
                      {task.start_time} - {task.end_time}
                    </div>
                  </div>
                </div>
              </div>
            )
          })}
        </div>
      </div>

      {/* Footer with summary */}
      <div style={{
        padding: '12px 20px',
        borderTop: '1px solid #e9ecef',
        background: '#fff',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: 13,
        color: '#666',
        flexWrap: 'wrap',
        gap: 8,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
          <span>{schedule.length} task{schedule.length !== 1 ? 's' : ''} scheduled</span>
          {showFullDay && (
            <span style={{
              padding: '2px 8px',
              background: 'rgba(0, 123, 255, 0.1)',
              borderRadius: 4,
              fontSize: 12,
              color: '#007bff',
            }}>
              {timeWindow.start_time} - {timeWindow.end_time}
            </span>
          )}
        </div>
        <div style={{ display: 'flex', gap: 16 }}>
          {Object.entries(CATEGORY_COLORS).map(([cat, colors]) => {
            const count = schedule.filter(t => t.category === cat).length
            if (count === 0) return null
            return (
              <div key={cat} style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                <div style={{
                  width: 12,
                  height: 12,
                  borderRadius: 3,
                  background: colors.bg,
                  border: `2px solid ${colors.border}`,
                }} />
                <span>{cat}: {count}</span>
              </div>
            )
          })}
        </div>
      </div>
    </div>
  )
}
