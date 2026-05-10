import { useState, useEffect, useCallback, useRef } from 'react'
import { 
  getStoredTheme, 
  setStoredTheme, 
  getSystemTheme, 
  applyThemeToDOM,
  LIGHT_THEME,
  DARK_THEME 
} from '../utils/themeUtils'
import { ThemeContext } from '../hooks/useTheme'

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
