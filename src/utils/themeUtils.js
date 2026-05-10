export const THEME_KEY = 'theme'
export const LIGHT_THEME = 'light'
export const DARK_THEME = 'dark'

export const getStoredTheme = () => {
  if (typeof window === 'undefined') return null
  try {
    return localStorage.getItem(THEME_KEY)
  } catch {
    return null
  }
}

export const setStoredTheme = (theme) => {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(THEME_KEY, theme)
  } catch (e) {
    console.warn('Failed to save theme to localStorage:', e)
  }
}

export const getSystemTheme = () => {
  if (typeof window === 'undefined') return LIGHT_THEME
  return window.matchMedia('(prefers-color-scheme: dark)').matches 
    ? DARK_THEME 
    : LIGHT_THEME
}

export const applyThemeToDOM = (theme) => {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-theme', theme)
}
