import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest'
import { render, screen, act } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { ThemeProvider, useTheme } from './ThemeContext'

const TestComponent = () => {
  const { theme, toggleTheme, setTheme } = useTheme()
  return (
    <div>
      <span data-testid="theme">{theme}</span>
      <button onClick={toggleTheme} data-testid="toggle">Toggle</button>
      <button onClick={() => setTheme('light')} data-testid="set-light">Set Light</button>
      <button onClick={() => setTheme('dark')} data-testid="set-dark">Set Dark</button>
      <button onClick={() => setTheme('invalid')} data-testid="set-invalid">Set Invalid</button>
    </div>
  )
}

describe('ThemeContext', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.useRealTimers()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Initialization', () => {
    it('should default to system preference when no localStorage value', () => {
      const matchMediaSpy = vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }))

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('theme')).toHaveTextContent('dark')
      matchMediaSpy.mockRestore()
    })

    it('should use localStorage value if available', () => {
      localStorage.setItem('theme', 'light')

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('theme')).toHaveTextContent('light')
      expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    })

    it('should use initialTheme prop if provided', () => {
      render(
        <ThemeProvider initialTheme="dark">
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('theme')).toHaveTextContent('dark')
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    })

    it('should handle invalid localStorage values gracefully', () => {
      localStorage.setItem('theme', 'invalid-value')
      const matchMediaSpy = vi.spyOn(window, 'matchMedia').mockImplementation((query) => ({
        matches: query === '(prefers-color-scheme: dark)',
        media: query,
        onchange: null,
        addListener: vi.fn(),
        removeListener: vi.fn(),
        addEventListener: vi.fn(),
        removeEventListener: vi.fn(),
        dispatchEvent: vi.fn(),
      }))

      render(
        <ThemeProvider>
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('theme')).toHaveTextContent('dark')
      matchMediaSpy.mockRestore()
    })
  })

  describe('Theme Toggle', () => {
    it('should toggle from light to dark', async () => {
      const user = userEvent.setup()
      render(
        <ThemeProvider initialTheme="light">
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('theme')).toHaveTextContent('light')

      await user.click(screen.getByTestId('toggle'))

      expect(screen.getByTestId('theme')).toHaveTextContent('dark')
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
      expect(localStorage.getItem('theme')).toBe('dark')
    })

    it('should toggle from dark to light', async () => {
      const user = userEvent.setup()
      render(
        <ThemeProvider initialTheme="dark">
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('theme')).toHaveTextContent('dark')

      await user.click(screen.getByTestId('toggle'))

      expect(screen.getByTestId('theme')).toHaveTextContent('light')
      expect(document.documentElement.getAttribute('data-theme')).toBe('light')
      expect(localStorage.getItem('theme')).toBe('light')
    })

    it('should handle rapid clicks with debounce', async () => {
      const user = userEvent.setup()
      render(
        <ThemeProvider initialTheme="light">
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('theme')).toHaveTextContent('light')

      await act(async () => {
        await user.click(screen.getByTestId('toggle'))
        await user.click(screen.getByTestId('toggle'))
        await user.click(screen.getByTestId('toggle'))
      })

      expect(screen.getByTestId('theme')).toHaveTextContent('dark')
    })
  })

  describe('setTheme Function', () => {
    it('should set theme to light', async () => {
      const user = userEvent.setup()
      render(
        <ThemeProvider initialTheme="dark">
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('theme')).toHaveTextContent('dark')

      await user.click(screen.getByTestId('set-light'))

      expect(screen.getByTestId('theme')).toHaveTextContent('light')
      expect(document.documentElement.getAttribute('data-theme')).toBe('light')
      expect(localStorage.getItem('theme')).toBe('light')
    })

    it('should set theme to dark', async () => {
      const user = userEvent.setup()
      render(
        <ThemeProvider initialTheme="light">
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('theme')).toHaveTextContent('light')

      await user.click(screen.getByTestId('set-dark'))

      expect(screen.getByTestId('theme')).toHaveTextContent('dark')
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
      expect(localStorage.getItem('theme')).toBe('dark')
    })

    it('should ignore invalid theme values', async () => {
      const user = userEvent.setup()
      render(
        <ThemeProvider initialTheme="light">
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('theme')).toHaveTextContent('light')

      await user.click(screen.getByTestId('set-invalid'))

      expect(screen.getByTestId('theme')).toHaveTextContent('light')
      expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    })
  })

  describe('localStorage Persistence', () => {
    it('should persist theme to localStorage on toggle', async () => {
      const user = userEvent.setup()
      render(
        <ThemeProvider initialTheme="light">
          <TestComponent />
        </ThemeProvider>
      )

      expect(localStorage.getItem('theme')).toBeNull()

      await user.click(screen.getByTestId('toggle'))

      expect(localStorage.getItem('theme')).toBe('dark')
    })

    it('should persist theme to localStorage on setTheme', async () => {
      const user = userEvent.setup()
      render(
        <ThemeProvider initialTheme="light">
          <TestComponent />
        </ThemeProvider>
      )

      await user.click(screen.getByTestId('set-dark'))

      expect(localStorage.getItem('theme')).toBe('dark')
    })
  })

  describe('useTheme Hook', () => {
    it('should throw error when used outside ThemeProvider', () => {
      const consoleErrorSpy = vi.spyOn(console, 'error').mockImplementation(() => {})
      
      expect(() => {
        render(<TestComponent />)
      }).toThrow('useTheme must be used within a ThemeProvider')

      consoleErrorSpy.mockRestore()
    })

    it('should return theme, toggleTheme, and setTheme', () => {
      render(
        <ThemeProvider initialTheme="light">
          <TestComponent />
        </ThemeProvider>
      )

      expect(screen.getByTestId('theme')).toBeInTheDocument()
      expect(screen.getByTestId('toggle')).toBeInTheDocument()
      expect(screen.getByTestId('set-light')).toBeInTheDocument()
      expect(screen.getByTestId('set-dark')).toBeInTheDocument()
    })
  })
})
