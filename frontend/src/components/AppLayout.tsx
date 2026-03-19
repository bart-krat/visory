import { ReactNode } from 'react'

type AppLayoutProps = {
  children: ReactNode
}

function getDaysInMonth(year: number, month: number): number {
  return new Date(year, month + 1, 0).getDate()
}

function getFirstDayOfMonth(year: number, month: number): number {
  return new Date(year, month, 1).getDay()
}

const WEEKDAYS = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
const MONTHS = [
  'January', 'February', 'March', 'April', 'May', 'June',
  'July', 'August', 'September', 'October', 'November', 'December'
]

function FullScreenCalendar() {
  const today = new Date()
  const currentYear = today.getFullYear()
  const currentMonth = today.getMonth()
  const currentDay = today.getDate()

  const daysInMonth = getDaysInMonth(currentYear, currentMonth)
  const firstDay = getFirstDayOfMonth(currentYear, currentMonth)

  const calendarDays: (number | null)[] = []

  for (let i = 0; i < firstDay; i++) {
    calendarDays.push(null)
  }

  for (let day = 1; day <= daysInMonth; day++) {
    calendarDays.push(day)
  }

  while (calendarDays.length < 42) { // 6 rows x 7 days
    calendarDays.push(null)
  }

  const isToday = (day: number | null) => day === currentDay

  return (
    <div style={{
      position: 'fixed',
      top: 0,
      left: 0,
      right: 0,
      bottom: 0,
      background: 'linear-gradient(135deg, #06b6d4 0%, #0891b2 100%)', // Turquoise gradient
      display: 'flex',
      flexDirection: 'column',
      padding: '20px',
      boxSizing: 'border-box',
      overflow: 'hidden',
    }}>
      {/* Month Header */}
      <div style={{
        textAlign: 'center',
        marginBottom: 16,
        flexShrink: 0,
      }}>
        <div style={{
          fontSize: 'clamp(24px, 5vw, 48px)',
          fontWeight: 700,
          color: 'rgba(255, 255, 255, 0.15)',
          letterSpacing: '0.05em',
        }}>
          {MONTHS[currentMonth].toUpperCase()}
        </div>
        <div style={{
          fontSize: 'clamp(14px, 2vw, 20px)',
          color: 'rgba(255, 255, 255, 0.1)',
          letterSpacing: '0.2em',
        }}>
          {currentYear}
        </div>
      </div>

      {/* Weekday Headers */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        gap: 4,
        marginBottom: 8,
        flexShrink: 0,
      }}>
        {WEEKDAYS.map(day => (
          <div
            key={day}
            style={{
              textAlign: 'center',
              fontSize: 'clamp(10px, 1.5vw, 14px)',
              fontWeight: 600,
              color: 'rgba(255, 255, 255, 0.2)',
              padding: '8px 0',
              letterSpacing: '0.1em',
            }}
          >
            {day.toUpperCase()}
          </div>
        ))}
      </div>

      {/* Calendar Grid - fills remaining space */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: 'repeat(7, 1fr)',
        gridTemplateRows: 'repeat(6, 1fr)',
        gap: 4,
        flex: 1,
        minHeight: 0,
      }}>
        {calendarDays.map((day, idx) => (
          <div
            key={idx}
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              borderRadius: 12,
              fontSize: 'clamp(16px, 3vw, 32px)',
              fontWeight: isToday(day) ? 700 : 400,
              color: day
                ? isToday(day)
                  ? 'rgba(255, 255, 255, 0.3)'
                  : 'rgba(255, 255, 255, 0.08)'
                : 'transparent',
              background: isToday(day)
                ? 'rgba(255, 255, 255, 0.1)'
                : 'transparent',
              border: isToday(day)
                ? '2px solid rgba(255, 255, 255, 0.2)'
                : '1px solid rgba(255, 255, 255, 0.03)',
            }}
          >
            {day}
          </div>
        ))}
      </div>
    </div>
  )
}

export default function AppLayout({ children }: AppLayoutProps) {
  return (
    <div style={{
      minHeight: '100vh',
      position: 'relative',
    }}>
      {/* Full-screen calendar background */}
      <FullScreenCalendar />

      {/* Content overlay */}
      <div style={{
        position: 'relative',
        zIndex: 10,
        minHeight: '100vh',
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        padding: '20px',
        boxSizing: 'border-box',
      }}>
        {/* App Header */}
        <div style={{
          textAlign: 'center',
          marginBottom: 20,
        }}>
          <h1 style={{
            margin: 0,
            fontSize: 'clamp(28px, 5vw, 40px)',
            fontWeight: 700,
            color: '#fff',
            letterSpacing: '-0.5px',
            textShadow: '0 2px 10px rgba(0, 0, 0, 0.2)',
          }}>
            Visory
          </h1>
          <p style={{
            margin: '4px 0 0 0',
            fontSize: 'clamp(14px, 2vw, 16px)',
            color: 'rgba(255, 255, 255, 0.8)',
          }}>
            Plan your day with AI
          </p>
        </div>

        {/* Main Content Card */}
        <div style={{
          width: '100%',
          maxWidth: 1100,
          background: 'rgba(255, 255, 255, 0.95)',
          backdropFilter: 'blur(20px)',
          borderRadius: 24,
          boxShadow: '0 20px 60px rgba(0, 0, 0, 0.3)',
          overflow: 'hidden',
          maxHeight: 'calc(100vh - 160px)',
          display: 'flex',
          flexDirection: 'column',
        }}>
          <div style={{
            padding: '24px',
            overflowY: 'auto',
            flex: 1,
          }}>
            {children}
          </div>
        </div>
      </div>
    </div>
  )
}
