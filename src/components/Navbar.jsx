import { useState, useEffect, useRef } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '../hooks/useTheme'
import Menu from './Menu'
import { menuItems } from '../data/menuData'
import './Navbar.css'

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const { theme, toggleTheme } = useTheme()
  const location = useLocation()
  const mobileMenuRef = useRef(null)
  const hamburgerRef = useRef(null)
  const locationRef = useRef(location)

  useEffect(() => {
    if (locationRef.current.pathname !== location.pathname) {
      setIsMenuOpen(false)
    }
    locationRef.current = location
  }, [location])

  useEffect(() => {
    const handleEscape = (e) => {
      if (e.key === 'Escape' && isMenuOpen) {
        setIsMenuOpen(false)
        hamburgerRef.current?.focus()
      }
    }

    const handleResize = () => {
      if (window.innerWidth > 768) {
        setIsMenuOpen(false)
      }
    }

    document.addEventListener('keydown', handleEscape)
    window.addEventListener('resize', handleResize)
    
    return () => {
      document.removeEventListener('keydown', handleEscape)
      window.removeEventListener('resize', handleResize)
    }
  }, [isMenuOpen])

  useEffect(() => {
    if (!isMenuOpen) return

    const menuEl = mobileMenuRef.current
    if (!menuEl) return

    const focusableElements = menuEl.querySelectorAll(
      'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
    )

    if (focusableElements && focusableElements.length > 0) {
      focusableElements[0].focus()
    }

    const handleKeyDown = (e) => {
      if (e.key !== 'Tab' || !focusableElements) return

      const firstElement = focusableElements[0]
      const lastElement = focusableElements[focusableElements.length - 1]

      if (e.shiftKey && document.activeElement === firstElement) {
        e.preventDefault()
        lastElement.focus()
      } else if (!e.shiftKey && document.activeElement === lastElement) {
        e.preventDefault()
        firstElement.focus()
      }
    }

    menuEl.addEventListener('keydown', handleKeyDown)
    return () => menuEl.removeEventListener('keydown', handleKeyDown)
  }, [isMenuOpen])

  const handleHamburgerKeyDown = (e) => {
    switch (e.key) {
      case 'Enter':
      case ' ':
        e.preventDefault()
        setIsMenuOpen(!isMenuOpen)
        break
    }
  }

  const handleNavigate = () => {
    setIsMenuOpen(false)
  }

  return (
    <nav className="navbar" role="navigation" aria-label="主导航">
      <div className="navbar-container">
        <NavLink to="/" end className="navbar-brand" aria-label="返回首页">
          MyApp
        </NavLink>

        <div className="desktop-menu" role="menubar">
          <Menu 
            items={menuItems} 
            orientation="horizontal"
            onNavigate={handleNavigate}
            ariaLabel="主菜单"
          />
          <button 
            className="theme-toggle" 
            onClick={toggleTheme}
            aria-label={theme === 'light' ? '切换到深色模式' : '切换到浅色模式'}
          >
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
        </div>

        <div className="mobile-menu-header">
          <button 
            className="theme-toggle" 
            onClick={toggleTheme}
            aria-label={theme === 'light' ? '切换到深色模式' : '切换到浅色模式'}
          >
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
          <button
            ref={hamburgerRef}
            className="hamburger"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            onKeyDown={handleHamburgerKeyDown}
            aria-label={isMenuOpen ? '关闭菜单' : '打开菜单'}
            aria-expanded={isMenuOpen}
            aria-controls="mobile-menu"
          >
            <span className={`hamburger-line ${isMenuOpen ? 'open' : ''}`}></span>
            <span className={`hamburger-line ${isMenuOpen ? 'open' : ''}`}></span>
            <span className={`hamburger-line ${isMenuOpen ? 'open' : ''}`}></span>
          </button>
        </div>

        <div 
          id="mobile-menu"
          ref={mobileMenuRef}
          className={`mobile-menu ${isMenuOpen ? 'open' : ''}`}
          role="dialog"
          aria-modal="true"
          aria-label="移动端导航菜单"
          aria-hidden={!isMenuOpen}
        >
          <Menu 
            items={menuItems} 
            orientation="mobile"
            onNavigate={handleNavigate}
            ariaLabel="移动端菜单"
          />
        </div>
      </div>
    </nav>
  )
}

export default Navbar
