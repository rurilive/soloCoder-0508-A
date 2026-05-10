import { useState, useEffect, useRef, useCallback } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import './Navbar.css'

const checkPathActive = (items, pathname) => {
  return items.some(item => {
    if (item.path === pathname) return true
    if (item.children) {
      return checkPathActive(item.children, pathname)
    }
    return false
  })
}

const menuItems = [
  {
    id: 1,
    label: '首页',
    path: '/',
  },
  {
    id: 2,
    label: '产品',
    path: '/products',
    children: [
      { id: 21, label: '产品列表', path: '/products/list' },
      { id: 22, label: '产品详情', path: '/products/detail' },
      {
        id: 23,
        label: '高级功能',
        children: [
          { id: 231, label: '功能A', path: '/products/advanced/a' },
          { id: 232, label: '功能B', path: '/products/advanced/b' },
        ],
      },
    ],
  },
  {
    id: 3,
    label: '服务',
    path: '/services',
    children: [
      { id: 31, label: '咨询服务', path: '/services/consulting' },
      { id: 32, label: '技术支持', path: '/services/support' },
    ],
  },
  {
    id: 4,
    label: '关于我们',
    path: '/about',
  },
]

const MenuItem = ({ item, isMobile, onNavigate }) => {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)
  const currentPath = useLocation().pathname

  const hasChildren = item.children && item.children.length > 0
  const isActive = item.path === currentPath || 
    (hasChildren && checkPathActive(item.children, currentPath))

  const handleKeyDown = useCallback((e) => {
    if (!hasChildren) return
    
    switch (e.key) {
      case 'Enter':
      case ' ':
        e.preventDefault()
        setIsOpen(!isOpen)
        break
      case 'Escape':
        e.preventDefault()
        setIsOpen(false)
        e.currentTarget.focus()
        break
      case 'ArrowDown':
        if (isOpen) {
          e.preventDefault()
          const firstFocusable = dropdownRef.current?.querySelector(
            'button, [href], input, select, textarea, [tabindex]:not([tabindex="-1"])'
          )
          firstFocusable?.focus()
        } else {
          setIsOpen(true)
        }
        break
      case 'ArrowRight':
        if (!isMobile && hasChildren) {
          e.preventDefault()
          setIsOpen(true)
        }
        break
      case 'ArrowLeft':
        if (!isMobile && isOpen) {
          e.preventDefault()
          setIsOpen(false)
        }
        break
    }
  }, [hasChildren, isOpen, isMobile])

  useEffect(() => {
    if (!hasChildren) return

    const handleClickOutside = (e) => {
      if (!isMobile && dropdownRef.current && !dropdownRef.current.contains(e.target)) {
        setIsOpen(false)
      }
    }

    const handleEscape = (e) => {
      if (e.key === 'Escape' && isOpen) {
        setIsOpen(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    document.addEventListener('keydown', handleEscape)
    
    return () => {
      document.removeEventListener('mousedown', handleClickOutside)
      document.removeEventListener('keydown', handleEscape)
    }
  }, [hasChildren, isMobile, isOpen])

  const handleLinkClick = useCallback(() => {
    if (onNavigate) {
      onNavigate()
    }
  }, [onNavigate])

  if (!hasChildren) {
    return (
      <NavLink
        to={item.path}
        className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
        onClick={handleLinkClick}
        aria-current={item.path === currentPath ? 'page' : undefined}
      >
        {item.label}
      </NavLink>
    )
  }

  return (
    <div 
      className="menu-item-dropdown"
      ref={dropdownRef}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) {
          if (!isMobile) setIsOpen(false)
        }
      }}
    >
      <button
        className={`nav-link dropdown-toggle ${isActive ? 'active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        onMouseEnter={() => !isMobile && setIsOpen(true)}
        onMouseLeave={() => !isMobile && setIsOpen(false)}
        onKeyDown={handleKeyDown}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-controls={`dropdown-${item.id}`}
      >
        {item.label}
        <span className={`arrow ${isOpen ? 'open' : ''}`} aria-hidden="true">▼</span>
      </button>
      <div 
        id={`dropdown-${item.id}`}
        className={`dropdown-menu ${isMobile ? 'mobile' : ''} ${isOpen ? 'open' : ''}`}
        onMouseEnter={() => !isMobile && setIsOpen(true)}
        onMouseLeave={() => !isMobile && setIsOpen(false)}
        role="menu"
        aria-hidden={!isOpen}
      >
        {item.children.map((child) => (
          <div 
            key={child.id} 
            className="dropdown-item-wrapper"
            role="none"
          >
            {child.children ? (
              <MenuItem 
                item={child} 
                isMobile={isMobile} 
                onNavigate={onNavigate}
              />
            ) : (
              <NavLink
                to={child.path}
                className={({ isActive }) => `dropdown-item ${isActive ? 'active' : ''}`}
                onClick={handleLinkClick}
                role="menuitem"
                tabIndex={isOpen ? 0 : -1}
                aria-current={child.path === currentPath ? 'page' : undefined}
                onKeyDown={(e) => {
                  if (e.key === 'Escape') {
                    e.preventDefault()
                    setIsOpen(false)
                  }
                }}
              >
                {child.label}
              </NavLink>
            )}
          </div>
        ))}
      </div>
    </div>
  )
}

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
          {menuItems.map((item) => (
            <div key={item.id} role="none">
              <MenuItem 
                key={item.id} 
                item={item} 
                isMobile={false}
                onNavigate={handleNavigate}
              />
            </div>
          ))}
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
          {menuItems.map((item) => (
            <MenuItem 
              key={item.id} 
              item={item} 
              isMobile={true}
              onNavigate={handleNavigate}
            />
          ))}
        </div>
      </div>
    </nav>
  )
}

export default Navbar