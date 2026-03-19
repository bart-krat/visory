// Color constants - Professional Turquoise Palette
export const colors = {
  // Primary turquoise shades
  primary: '#14b8a6',        // Turquoise 500 - main brand color
  primaryLight: '#5eead4',   // Turquoise 300 - lighter accent
  primaryDark: '#0f766e',    // Turquoise 700 - darker shade
  primaryPale: '#ccfbf1',    // Turquoise 100 - very light background

  // Gradient colors
  gradientStart: '#06b6d4',  // Cyan 500
  gradientEnd: '#0891b2',    // Cyan 600

  // Semantic colors
  success: '#10b981',        // Green 500
  danger: '#ef4444',         // Red 500
  warning: '#f59e0b',        // Amber 500
  info: '#3b82f6',           // Blue 500

  // Neutral palette
  gray: '#64748b',           // Slate 500
  lightGray: '#f1f5f9',      // Slate 100
  border: '#cbd5e1',         // Slate 300
  borderLight: '#e2e8f0',    // Slate 200
  textPrimary: '#0f172a',    // Slate 900
  textSecondary: '#64748b',  // Slate 500
  white: '#ffffff',
  black: '#000000',
  backgroundLight: '#f8fafc', // Slate 50
  backgroundDark: '#1e293b',  // Slate 800
}

// Spacing constants
export const spacing = {
  xs: 4,
  sm: 8,
  md: 12,
  lg: 16,
  xl: 24,
  xxl: 32,
}

// Border radius constants
export const borderRadius = {
  sm: 4,
  md: 6,
  lg: 8,
  xl: 16,
}

// Button styles
export const buttonStyles = {
  primary: {
    padding: '12px 24px',
    borderRadius: borderRadius.lg,
    background: colors.primary,
    color: colors.white,
    border: 'none',
    fontSize: 14,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    boxShadow: '0 1px 2px 0 rgba(0, 0, 0, 0.05)',
  },
  secondary: {
    padding: '6px 12px',
    borderRadius: borderRadius.md,
    background: colors.white,
    border: `1px solid ${colors.primary}`,
    color: colors.primary,
    fontSize: 12,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  success: {
    padding: '6px 12px',
    borderRadius: borderRadius.md,
    background: colors.success,
    border: 'none',
    color: colors.white,
    fontSize: 12,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  outlined: {
    padding: '10px 20px',
    borderRadius: borderRadius.md,
    background: 'transparent',
    border: `2px solid ${colors.primary}`,
    color: colors.primary,
    fontSize: 14,
    fontWeight: 500,
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
}

// Category emojis
export const categoryEmojis: Record<string, string> = {
  health: '💪',
  work: '💼',
  personal: '🎮',
}

// Phase labels
export const phaseLabels: Record<string, string> = {
  'welcome': 'Welcome',
  'questionnaire': 'Values Assessment',
  'evaluation_complete': 'Assessment Complete',
  'collect_tasks': 'Task Collection',
  'constraints': 'Time Constraints',
  'constraint_clarification': 'Optimization Preferences',
  'optimize': 'Optimizing...',
  'complete': 'Complete',
}
