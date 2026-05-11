import React, { useState, useEffect } from 'react'
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import Home from './pages/Home'
import AdminLogin from './pages/AdminLogin'
import AdminDashboard from './pages/AdminDashboard'
import './App.css'

function App() {
  const [token, setToken] = useState(null)

  useEffect(() => {
    const savedToken = localStorage.getItem('admin_token')
    if (savedToken) {
      setToken(savedToken)
    }
  }, [])

  const handleLogin = (newToken) => {
    setToken(newToken)
    localStorage.setItem('admin_token', newToken)
  }

  const handleLogout = () => {
    setToken(null)
    localStorage.removeItem('admin_token')
  }

  return (
    <Router>
      <div className="app">
        <Routes>
          <Route path="/" element={<Home />} />
          <Route 
            path="/admin/login" 
            element={
              token ? (
                <Navigate to="/admin" replace />
              ) : (
                <AdminLogin onLogin={handleLogin} />
              )
            } 
          />
          <Route 
            path="/admin" 
            element={
              token ? (
                <AdminDashboard token={token} onLogout={handleLogout} />
              ) : (
                <Navigate to="/admin/login" replace />
              )
            } 
          />
        </Routes>
      </div>
    </Router>
  )
}

export default App
