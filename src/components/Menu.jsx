import { useState, useEffect, useRef, useCallback } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '../hooks/useTheme'
import { checkPathActive } from '../utils/menuUtils'
import './Menu.css'

const MenuItem = ({ 
  item, 
  orientation = 'horizontal', 
  onNavigate,
  level = 0
}) => {
  const [isOpen, setIsOpen] = useState(false)
  const dropdownRef = useRef(null)
  const currentPath = useLocation().pathname
  const isVertical = orientation === 'vertical'
  const isMobile = orientation === 'mobile'

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
        if (!isMobile && hasChildren && !isVertical) {
          e.preventDefault()
          setIsOpen(true)
        }
        break
      case 'ArrowLeft':
        if (!isMobile && isOpen && !isVertical) {
          e.preventDefault()
          setIsOpen(false)
        }
        break
      case 'ArrowUp':
        if (isVertical && hasChildren) {
          e.preventDefault()
          setIsOpen(!isOpen)
        }
        break
    }
  }, [hasChildren, isOpen, isMobile, isVertical])

  useEffect(() => {
    if (!hasChildren) return

    const handleClickOutside = (e) => {
      if (!isMobile && !isVertical && dropdownRef.current && !dropdownRef.current.contains(e.target)) {
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
  }, [hasChildren, isMobile, isVertical, isOpen])

  const handleLinkClick = useCallback(() => {
    if (onNavigate) {
      onNavigate()
    }
  }, [onNavigate])

  if (!hasChildren) {
    return (
      <NavLink
        to={item.path}
        className={({ isActive }) => `menu-link ${isActive ? 'active' : ''}`}
        onClick={handleLinkClick}
        aria-current={item.path === currentPath ? 'page' : undefined}
        style={{ paddingLeft: isVertical ? `${1 + level * 0.5}rem` : undefined }}
      >
        {item.label}
      </NavLink>
    )
  }

  return (
    <div 
      className={`menu-item-dropdown ${orientation}`}
      ref={dropdownRef}
      onBlur={(e) => {
        if (!e.currentTarget.contains(e.relatedTarget)) {
          if (!isMobile && !isVertical) setIsOpen(false)
        }
      }}
    >
      <button
        className={`menu-link dropdown-toggle ${isActive ? 'active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        onMouseEnter={() => !isMobile && !isVertical && setIsOpen(true)}
        onMouseLeave={() => !isMobile && !isVertical && setIsOpen(false)}
        onKeyDown={handleKeyDown}
        aria-expanded={isOpen}
        aria-haspopup="menu"
        aria-controls={`dropdown-${item.id}`}
        style={{ paddingLeft: isVertical ? `${1 + level * 0.5}rem` : undefined }}
      >
        {item.label}
        <span className={`arrow ${isOpen ? 'open' : ''}`} aria-hidden="true">
          {isVertical || isMobile ? '▶' : '▼'}
        </span>
      </button>
      <div 
        id={`dropdown-${item.id}`}
        className={`dropdown-menu ${orientation} ${isOpen ? 'open' : ''}`}
        onMouseEnter={() => !isMobile && !isVertical && setIsOpen(true)}
        onMouseLeave={() => !isMobile && !isVertical && setIsOpen(false)}
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
                orientation={orientation}
                onNavigate={onNavigate}
                level={level + 1}
              />
            ) : (
              <NavLink
                to={child.path}
                className={({ isActive }) => `dropdown-item ${isActive ? 'active' : ''}`}
                onClick={handleLinkClick}
                role="menuitem"
                tabIndex={isOpen ? 0 : -1}
                aria-current={child.path === currentPath ? 'page' : undefined}
                style={{ paddingLeft: isVertical ? `${1 + (level + 1) * 0.5}rem` : undefined }}
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

const Menu = ({
  items,
  orientation = 'horizontal',
  className = '',
  onNavigate,
  ariaLabel = '菜单',
}) => {
  const { theme } = useTheme()
  
  const containerClass = `menu menu-${orientation} ${className} theme-${theme}`

  return (
    <div className={containerClass} role={orientation === 'horizontal' ? 'menubar' : 'menu'} aria-label={ariaLabel}>
      {items.map((item) => (
        <div key={item.id} role="none">
          <MenuItem 
            item={item} 
            orientation={orientation}
            onNavigate={onNavigate}
            level={0}
          />
        </div>
      ))}
    </div>
  )
}

export default Menu
