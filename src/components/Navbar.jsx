import { useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'
import { useTheme } from '../contexts/ThemeContext'
import './Navbar.css'

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

const MenuItem = ({ item, isMobile }) => {
  const [isOpen, setIsOpen] = useState(false)
  const location = useLocation()

  const hasChildren = item.children && item.children.length > 0
  const isActive = item.path === location.pathname || 
    (hasChildren && item.children.some(child => location.pathname.startsWith(child.path || '/')))

  if (!hasChildren) {
    return (
      <NavLink
        to={item.path}
        end={item.path === '/'}
        className={({ isActive }) => `nav-link ${isActive ? 'active' : ''}`}
      >
        {item.label}
      </NavLink>
    )
  }

  return (
    <div className="menu-item-dropdown">
      <button
        className={`nav-link dropdown-toggle ${isActive ? 'active' : ''}`}
        onClick={() => setIsOpen(!isOpen)}
        onMouseEnter={() => !isMobile && setIsOpen(true)}
        onMouseLeave={() => !isMobile && setIsOpen(false)}
      >
        {item.label}
        <span className={`arrow ${isOpen ? 'open' : ''}`}>▼</span>
      </button>
      {isOpen && (
        <div 
          className={`dropdown-menu ${isMobile ? 'mobile' : ''}`}
          onMouseEnter={() => !isMobile && setIsOpen(true)}
          onMouseLeave={() => !isMobile && setIsOpen(false)}
        >
          {item.children.map((child) => (
            <div key={child.id} className="dropdown-item-wrapper">
              {child.children ? (
                <MenuItem item={child} isMobile={isMobile} />
              ) : (
                <NavLink
                  to={child.path}
                  end={child.path === '/'}
                  className={({ isActive }) => `dropdown-item ${isActive ? 'active' : ''}`}
                >
                  {child.label}
                </NavLink>
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

const Navbar = () => {
  const [isMenuOpen, setIsMenuOpen] = useState(false)
  const { theme, toggleTheme } = useTheme()

  return (
    <nav className="navbar">
      <div className="navbar-container">
        <NavLink to="/" className="navbar-brand">
          MyApp
        </NavLink>

        <div className="desktop-menu">
          {menuItems.map((item) => (
            <MenuItem key={item.id} item={item} isMobile={false} />
          ))}
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
        </div>

        <div className="mobile-menu-header">
          <button className="theme-toggle" onClick={toggleTheme}>
            {theme === 'light' ? '🌙' : '☀️'}
          </button>
          <button
            className="hamburger"
            onClick={() => setIsMenuOpen(!isMenuOpen)}
            aria-label="Toggle menu"
          >
            <span className={`hamburger-line ${isMenuOpen ? 'open' : ''}`}></span>
            <span className={`hamburger-line ${isMenuOpen ? 'open' : ''}`}></span>
            <span className={`hamburger-line ${isMenuOpen ? 'open' : ''}`}></span>
          </button>
        </div>

        {isMenuOpen && (
          <div className="mobile-menu">
            {menuItems.map((item) => (
              <MenuItem key={item.id} item={item} isMobile={true} />
            ))}
          </div>
        )}
      </div>
    </nav>
  )
}

export default Navbar
