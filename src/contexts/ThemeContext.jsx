import { createContext, useContext, useState, useEffect, useCallback, useRef } from 'react'

const ThemeContext = createContext(null)

const THEME_KEY = 'theme'
const LIGHT_THEME = 'light'
const DARK_THEME = 'dark'

const getStoredTheme = () => {
  if (typeof window === 'undefined') return null
  try {
    return localStorage.getItem(THEME_KEY)
  } catch {
    return null
  }
}

const setStoredTheme = (theme) => {
  if (typeof window === 'undefined') return
  try {
    localStorage.setItem(THEME_KEY, theme)
  } catch (e) {
    console.warn('Failed to save theme to localStorage:', e)
  }
}

const getSystemTheme = () => {
  if (typeof window === 'undefined') return LIGHT_THEME
  return window.matchMedia('(prefers-color-scheme: dark)').matches 
    ? DARK_THEME 
    : LIGHT_THEME
}

const applyThemeToDOM = (theme) => {
  if (typeof document === 'undefined') return
  document.documentElement.setAttribute('data-theme', theme)
}

export const ThemeProvider = ({ children, initialTheme }) => {
  const [theme, setThemeState] = useState(() => {
    if (initialTheme) {
      return initialTheme
    }
    const stored = getStoredTheme()
    if (stored === LIGHT_THEME || stored === DARK_THEME) {
      return stored
    }
    return getSystemTheme()
  })

  const isTransitioningRef = useRef(false)

  const setTheme = useCallback((newTheme) => {
    if (newTheme !== LIGHT_THEME && newTheme !== DARK_THEME) {
      return
    }
    setThemeState(newTheme)
    setStoredTheme(newTheme)
    applyThemeToDOM(newTheme)
  }, [])

  const toggleTheme = useCallback(() => {
    if (isTransitioningRef.current) {
      return
    }
    isTransitioningRef.current = true

    setThemeState((prev) => {
      const nextTheme = prev === LIGHT_THEME ? DARK_THEME : LIGHT_THEME
      setStoredTheme(nextTheme)
      applyThemeToDOM(nextTheme)
      return nextTheme
    })

    requestAnimationFrame(() => {
      requestAnimationFrame(() => {
        isTransitioningRef.current = false
      })
    })
  }, [])

  useEffect(() => {
    applyThemeToDOM(theme)
  }, [theme])

  useEffect(() => {
    if (getStoredTheme()) {
      return
    }

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)')
    
    const handleSystemThemeChange = (e) => {
      const stored = getStoredTheme()
      if (!stored) {
        const systemTheme = e.matches ? DARK_THEME : LIGHT_THEME
        setThemeState(systemTheme)
      }
    }

    if (typeof mediaQuery.addEventListener === 'function') {
      mediaQuery.addEventListener('change', handleSystemThemeChange)
    } else {
      mediaQuery.addListener(handleSystemThemeChange)
    }

    return () => {
      if (typeof mediaQuery.removeEventListener === 'function') {
        mediaQuery.removeEventListener('change', handleSystemThemeChange)
      } else {
        mediaQuery.removeListener(handleSystemThemeChange)
      }
    }
  }, [])

  return (
    <ThemeContext.Provider value={{ theme, toggleTheme, setTheme }}>
      {children}
    </ThemeContext.Provider>
  )
}

export const useTheme = () => {
  const context = useContext(ThemeContext)
  if (!context) {
    throw new Error('useTheme must be used within a ThemeProvider')
  }
  return context
}
