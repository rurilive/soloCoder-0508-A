import { NavLink, useLocation } from 'react-router-dom'
import { getBreadcrumbPath } from '../utils/menuUtils'
import { menuItems } from '../data/menuData'
import './Breadcrumb.css'

const Breadcrumb = ({ items = menuItems }) => {
  const location = useLocation()
  const pathname = location.pathname
  
  const breadcrumbItems = getBreadcrumbPath(items, pathname)
  
  if (!breadcrumbItems || breadcrumbItems.length === 0) {
    return null
  }

  return (
    <nav className="breadcrumb" aria-label="面包屑导航">
      <ol className="breadcrumb-list">
        {breadcrumbItems.map((item, index) => {
          const isLast = index === breadcrumbItems.length - 1
          
          return (
            <li 
              key={item.path} 
              className="breadcrumb-item"
              aria-current={isLast ? 'page' : undefined}
            >
              {isLast ? (
                <span className="breadcrumb-current">{item.label}</span>
              ) : (
                <>
                  <NavLink 
                    to={item.path}
                    className="breadcrumb-link"
                    end
                  >
                    {item.label}
                  </NavLink>
                  <span className="breadcrumb-separator" aria-hidden="true">/</span>
                </>
              )}
            </li>
          )
        })}
      </ol>
    </nav>
  )
}

export default Breadcrumb
