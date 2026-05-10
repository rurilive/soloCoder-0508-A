import { Outlet } from 'react-router-dom'
import Navbar from './Navbar'
import Breadcrumb from './Breadcrumb'
import './Layout.css'

const Layout = () => {
  return (
    <div className="layout">
      <Navbar />
      <main className="main-content">
        <div className="container">
          <Breadcrumb />
          <Outlet />
        </div>
      </main>
    </div>
  )
}

export default Layout
