import { describe, it, expect, beforeEach, vi, afterEach } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Routes, Route } from 'react-router-dom'
import { ThemeProvider } from '../contexts/ThemeContext'
import Navbar from './Navbar'

const renderWithProviders = ({ initialRoute = '/', initialTheme } = {}) => {
  return render(
    <MemoryRouter initialEntries={[initialRoute]}>
      <ThemeProvider initialTheme={initialTheme}>
        <Navbar />
        <Routes>
          <Route path="/" element={<div>Home</div>} />
          <Route path="/products" element={<div>Products</div>} />
          <Route path="/products/list" element={<div>Product List</div>} />
          <Route path="/products/detail" element={<div>Product Detail</div>} />
          <Route path="/products/advanced/a" element={<div>Advanced A</div>} />
          <Route path="/products/advanced/b" element={<div>Advanced B</div>} />
          <Route path="/services/consulting" element={<div>Consulting</div>} />
          <Route path="/services/support" element={<div>Support</div>} />
          <Route path="/about" element={<div>About</div>} />
        </Routes>
      </ThemeProvider>
    </MemoryRouter>
  )
}

const getDesktopMenu = (container) => {
  return container.querySelector('.desktop-menu')
}

describe('Navbar Component', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  describe('Menu Rendering', () => {
    it('should render all top-level menu items', () => {
      const { container } = renderWithProviders()
      const desktopMenu = getDesktopMenu(container)
      
      expect(desktopMenu.textContent).toContain('首页')
      expect(desktopMenu.textContent).toContain('产品')
      expect(desktopMenu.textContent).toContain('服务')
      expect(desktopMenu.textContent).toContain('关于我们')
    })

    it('should render brand link', () => {
      renderWithProviders()
      
      const brandLink = screen.getByText('MyApp')
      expect(brandLink).toBeInTheDocument()
      expect(brandLink.closest('a')).toHaveAttribute('href', '/')
    })
  })

  describe('Active State and Highlight', () => {
    it('should highlight active menu item based on current route', () => {
      const { container } = renderWithProviders({ initialRoute: '/products/list' })
      const desktopMenu = getDesktopMenu(container)
      
      const productsButton = desktopMenu.querySelector('button.dropdown-toggle')
      expect(productsButton).toHaveClass('active')
    })

    it('should highlight root route correctly', () => {
      const { container } = renderWithProviders({ initialRoute: '/' })
      const desktopMenu = getDesktopMenu(container)
      
      const homeLinks = desktopMenu.querySelectorAll('a.nav-link[href="/"]')
      expect(homeLinks[0]).toHaveClass('active')
    })

    it('should highlight nested routes correctly', () => {
      const { container } = renderWithProviders({ initialRoute: '/products/advanced/a' })
      const desktopMenu = getDesktopMenu(container)
      
      const productsButton = desktopMenu.querySelector('button.dropdown-toggle')
      expect(productsButton).toHaveClass('active')
    })

    it('should set aria-current="page" on active link', () => {
      const { container } = renderWithProviders({ initialRoute: '/about' })
      const desktopMenu = getDesktopMenu(container)
      
      const aboutLinks = desktopMenu.querySelectorAll('a.nav-link[href="/about"]')
      expect(aboutLinks[0]).toHaveAttribute('aria-current', 'page')
    })
  })

  describe('Theme Toggle', () => {
    it('should render theme toggle button', () => {
      renderWithProviders()
      
      const themeButtons = screen.getAllByRole('button', { name: /切换到/ })
      expect(themeButtons.length).toBeGreaterThan(0)
    })

    it('should toggle theme from light to dark', async () => {
      const user = userEvent.setup()
      renderWithProviders({ initialTheme: 'light' })
      
      expect(document.documentElement.getAttribute('data-theme')).toBe('light')
      
      const themeButtons = screen.getAllByRole('button', { name: /切换到深色模式/ })
      await user.click(themeButtons[0])
      
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
    })

    it('should toggle theme from dark to light', async () => {
      const user = userEvent.setup()
      renderWithProviders({ initialTheme: 'dark' })
      
      expect(document.documentElement.getAttribute('data-theme')).toBe('dark')
      
      const themeButtons = screen.getAllByRole('button', { name: /切换到浅色模式/ })
      await user.click(themeButtons[0])
      
      expect(document.documentElement.getAttribute('data-theme')).toBe('light')
    })

    it('should persist theme to localStorage', async () => {
      const user = userEvent.setup()
      renderWithProviders({ initialTheme: 'light' })
      
      const themeButtons = screen.getAllByRole('button', { name: /切换到深色模式/ })
      await user.click(themeButtons[0])
      
      expect(localStorage.getItem('theme')).toBe('dark')
    })
  })

  describe('ARIA Attributes', () => {
    it('should have correct ARIA attributes on navbar', () => {
      renderWithProviders()
      
      const nav = screen.getByRole('navigation', { name: /主导航/ })
      expect(nav).toBeInTheDocument()
    })

    it('should have correct aria-haspopup on dropdown button', () => {
      const { container } = renderWithProviders()
      const desktopMenu = getDesktopMenu(container)
      
      const productsButton = desktopMenu.querySelector('button.dropdown-toggle')
      expect(productsButton).toHaveAttribute('aria-haspopup', 'menu')
    })

    it('should have correct aria-controls on dropdown button', async () => {
      const { container } = renderWithProviders()
      const desktopMenu = getDesktopMenu(container)
      
      const productsButton = desktopMenu.querySelector('button.dropdown-toggle')
      expect(productsButton).toHaveAttribute('aria-controls', 'dropdown-2')
    })
  })

  describe('Keyboard Navigation', () => {
    it('should open menu with ArrowRight key on desktop', async () => {
      const { container } = renderWithProviders()
      const desktopMenu = getDesktopMenu(container)
      const productsButton = desktopMenu.querySelector('button.dropdown-toggle')
      productsButton.focus()
      
      fireEvent.keyDown(productsButton, { key: 'ArrowRight' })
      
      expect(productsButton).toHaveAttribute('aria-expanded', 'true')
    })

    it('should close menu with ArrowLeft key on desktop', async () => {
      const { container } = renderWithProviders()
      const desktopMenu = getDesktopMenu(container)
      const productsButton = desktopMenu.querySelector('button.dropdown-toggle')
      productsButton.focus()
      
      fireEvent.keyDown(productsButton, { key: 'ArrowRight' })
      expect(productsButton).toHaveAttribute('aria-expanded', 'true')
      
      fireEvent.keyDown(productsButton, { key: 'ArrowLeft' })
      expect(productsButton).toHaveAttribute('aria-expanded', 'false')
    })
  })
})
