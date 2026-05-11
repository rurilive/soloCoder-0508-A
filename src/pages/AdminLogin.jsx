import React, { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import './AdminLogin.css'

const AdminLogin = ({ onLogin }) => {
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const navigate = useNavigate()

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setLoading(true)

    try {
      const response = await fetch('/api/admin/login', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ username, password }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || '登录失败')
      }

      const data = await response.json()
      onLogin(data.access_token)
      navigate('/admin')
    } catch (err) {
      setError(err.message || '登录失败')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="login-container">
      <div className="login-card">
        <h1 className="login-title">管理员登录</h1>
        <p className="login-subtitle">请输入管理员账号和密码</p>
        
        <form className="login-form" onSubmit={handleSubmit}>
          <div className="form-group">
            <label htmlFor="username">用户名</label>
            <input
              type="text"
              id="username"
              className="form-input"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="请输入用户名"
              required
            />
          </div>
          
          <div className="form-group">
            <label htmlFor="password">密码</label>
            <input
              type="password"
              id="password"
              className="form-input"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="请输入密码"
              required
            />
          </div>
          
          {error && (
            <div className="error-message">
              {error}
            </div>
          )}
          
          <button
            type="submit"
            className="login-btn"
            disabled={loading}
          >
            {loading ? '登录中...' : '登录'}
          </button>
        </form>
        
        <div className="login-footer">
          <p>默认账号: admin / admin123</p>
          <p className="note">请在生产环境中修改默认密码</p>
        </div>
      </div>
    </div>
  )
}

export default AdminLogin
