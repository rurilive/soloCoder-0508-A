import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import './AdminDashboard.css'

const AISettings = ({ token }) => {
  const navigate = useNavigate()
  const [config, setConfig] = useState({
    base_url: '',
    api_key: '',
    model: ''
  })
  const [loading, setLoading] = useState(false)
  const [saving, setSaving] = useState(false)
  const [message, setMessage] = useState('')
  const [error, setError] = useState('')

  useEffect(() => {
    if (!token) {
      navigate('/admin/login')
      return
    }
    fetchConfig()
  }, [token, navigate])

  const fetchConfig = async () => {
    setLoading(true)
    try {
      const response = await fetch('/api/admin/ai-config', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setConfig({
          base_url: data.base_url,
          api_key: '',
          model: data.model
        })
        setMessage('已加载配置')
      } else if (response.status !== 404) {
        setError('加载配置失败')
      }
    } catch (err) {
      console.error('加载配置失败:', err)
    } finally {
      setLoading(false)
    }
  }

  const handleSubmit = async (e) => {
    e.preventDefault()
    if (!config.base_url || !config.api_key || !config.model) {
      setError('请填写所有字段')
      return
    }

    setSaving(true)
    setError('')
    setMessage('')

    try {
      const response = await fetch('/api/admin/ai-config', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify(config)
      })

      if (response.ok) {
        setMessage('配置保存成功！')
        setConfig(c => ({ ...c, api_key: '' }))
      } else {
        const data = await response.json()
        setError(data.detail || '保存失败')
      }
    } catch (err) {
      setError('保存失败: ' + err.message)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className="admin-container">
      <header className="admin-header">
        <div className="header-content">
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <button 
              className="btn btn-secondary" 
              onClick={() => navigate('/admin')}
            >
              ← 返回列表
            </button>
            <h1 className="admin-title">AI 设置</h1>
          </div>
        </div>
      </header>

      <main className="admin-main" style={{ maxWidth: '600px', margin: '0 auto' }}>
        {message && (
          <div className="success-message">
            {message}
          </div>
        )}

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        <div className="settings-card">
          <h2>OpenAI 兼容接口配置</h2>
          <p className="settings-description">
            配置后可以使用批量AI审核功能，无需每次审核都重新输入配置
          </p>

          <form onSubmit={handleSubmit} className="settings-form">
            <div className="form-group">
              <label htmlFor="base_url">API Base URL</label>
              <input
                id="base_url"
                type="text"
                className="form-input"
                value={config.base_url}
                onChange={(e) => setConfig(c => ({ ...c, base_url: e.target.value }))}
                placeholder="例如: https://api.openai.com"
              />
            </div>

            <div className="form-group">
              <label htmlFor="api_key">API Key</label>
              <input
                id="api_key"
                type="password"
                className="form-input"
                value={config.api_key}
                onChange={(e) => setConfig(c => ({ ...c, api_key: e.target.value }))}
                placeholder="请输入API密钥"
              />
              <small style={{ color: '#666' }}>密钥将被加密存储，不会显示在页面上</small>
            </div>

            <div className="form-group">
              <label htmlFor="model">Model</label>
              <input
                id="model"
                type="text"
                className="form-input"
                value={config.model}
                onChange={(e) => setConfig(c => ({ ...c, model: e.target.value }))}
                placeholder="例如: gpt-3.5-turbo"
              />
            </div>

            <div className="form-actions">
              <button 
                type="button" 
                className="btn btn-secondary"
                onClick={() => navigate('/admin')}
              >
                取消
              </button>
              <button 
                type="submit" 
                className="btn btn-primary"
                disabled={saving || loading}
              >
                {saving ? '保存中...' : '保存配置'}
              </button>
            </div>
          </form>
        </div>

        <div className="tips-section" style={{ marginTop: '24px' }}>
          <h4>使用提示</h4>
          <ul>
            <li>支持所有 OpenAI 兼容的 API 接口</li>
            <li>配置保存后，管理员可以使用批量 AI 审核功能</li>
            <li>可以随时更新配置，新配置立即生效</li>
            <li>建议使用具有适当速率限制的 API Key</li>
          </ul>
        </div>
      </main>
    </div>
  )
}

export default AISettings
