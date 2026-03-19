// Color constants
export const colors = {
  primary: '#007bff',
  success: '#28a745',
  danger: '#dc3545',
  warning: '#ffc107',
  gray: '#666',
  lightGray: '#f8f9fa',
  border: '#ccc',
  borderLight: '#dee2e6',
  textSecondary: '#888',
  white: '#fff',
  black: '#000',
  backgroundLight: '#e9ecef',
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
  },
  secondary: {
    padding: '6px 12px',
    borderRadius: borderRadius.md,
    background: colors.white,
    border: `1px solid ${colors.primary}`,
    color: colors.primary,
    fontSize: 12,
  },
  success: {
    padding: '6px 12px',
    borderRadius: borderRadius.md,
    background: colors.success,
    border: 'none',
    color: colors.white,
    fontSize: 12,
    fontWeight: 500,
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
