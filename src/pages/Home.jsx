import React, { useState } from 'react'
import { Link } from 'react-router-dom'
import './Home.css'

const Home = () => {
  const [url, setUrl] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [result, setResult] = useState(null)
  const [stats, setStats] = useState(null)
  const [statsLoading, setStatsLoading] = useState(false)

  const handleSubmit = async (e) => {
    e.preventDefault()
    setError('')
    setResult(null)
    setLoading(true)

    try {
      const response = await fetch('/api/shorten', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({ url }),
      })

      if (!response.ok) {
        const data = await response.json()
        throw new Error(data.detail || '请求失败')
      }

      const data = await response.json()
      setResult(data)
    } catch (err) {
      setError(err.message || '发生错误')
    } finally {
      setLoading(false)
    }
  }

  const fetchStats = async () => {
    setStatsLoading(true)
    try {
      const response = await fetch('/api/stats')
      const data = await response.json()
      setStats(data)
    } catch (err) {
      console.error('获取统计数据失败:', err)
    } finally {
      setStatsLoading(false)
    }
  }

  const copyToClipboard = async (text) => {
    try {
      await navigator.clipboard.writeText(text)
      alert('已复制到剪贴板')
    } catch (err) {
      console.error('复制失败:', err)
    }
  }

  const shortUrl = result ? `http://localhost:1111/${result.short_code}` : ''

  return (
    <div className="home-container">
      <div className="home-content">
        <h1 className="title">URL 缩短服务</h1>
        <p className="subtitle">将长链接转换为简洁易分享的短链接</p>

        <form className="form" onSubmit={handleSubmit}>
          <div className="input-group">
            <input
              type="url"
              className="input"
              placeholder="请输入要缩短的 URL，例如：https://example.com"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              required
            />
            <button
              type="submit"
              className="submit-btn"
              disabled={loading || !url}
            >
              {loading ? '处理中...' : '缩短'}
            </button>
          </div>
        </form>

        {error && (
          <div className="error-message">
            {error}
          </div>
        )}

        {result && (
          <div className="result-card">
            <h3>缩短成功！</h3>
            <div className="result-item">
              <span className="label">原始链接:</span>
              <a href={result.original_url} target="_blank" rel="noopener noreferrer">
                {result.original_url}
              </a>
            </div>
            <div className="result-item">
              <span className="label">短链接:</span>
              <div className="short-url-group">
                <a href={shortUrl} target="_blank" rel="noopener noreferrer">
                  {shortUrl}
                </a>
                <button
                  type="button"
                  className="copy-btn"
                  onClick={() => copyToClipboard(shortUrl)}
                >
                  复制
                </button>
              </div>
            </div>
            {result.is_reused && (
              <div className="warning-message">
                提示：由于短码池已满，该短码是从最少使用的链接回收的。
                被替换的链接: {result.replaced_url}
              </div>
            )}
          </div>
        )}

        <div className="stats-section">
          <button
            type="button"
            className="stats-btn"
            onClick={fetchStats}
            disabled={statsLoading}
          >
            {statsLoading ? '加载中...' : '查看统计数据'}
          </button>

          {stats && (
            <div className="stats-card">
              <h3>短码池统计</h3>
              <div className="stats-grid">
                <div className="stat-item">
                  <span className="stat-value">{stats.total_pool.toLocaleString()}</span>
                  <span className="stat-label">总容量</span>
                </div>
                <div className="stat-item">
                  <span className="stat-value">{stats.used_count.toLocaleString()}</span>
                  <span className="stat-label">已使用</span>
                </div>
                <div className="stat-item">
                  <span className="stat-value">{stats.available_count.toLocaleString()}</span>
                  <span className="stat-label">可用</span>
                </div>
                <div className="stat-item">
                  <span className="stat-value">{stats.usage_percent}%</span>
                  <span className="stat-label">使用率</span>
                </div>
              </div>
              <div className="stats-details">
                {stats.oldest_accessed && (
                  <div className="detail-item">
                    <span>最早访问:</span>
                    <span>{new Date(stats.oldest_accessed).toLocaleString()}</span>
                  </div>
                )}
                {stats.newest_accessed && (
                  <div className="detail-item">
                    <span>最新访问:</span>
                    <span>{new Date(stats.newest_accessed).toLocaleString()}</span>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        <div className="info-section">
          <h3>使用说明</h3>
          <ul>
            <li>输入完整的 URL（包含 http:// 或 https://）</li>
            <li>短码长度为 6 位，使用大小写字母和数字</li>
            <li>当短码池满时，会自动替换最少使用的短码（LRU 策略）</li>
            <li>每次访问短链接会更新该链接的访问时间</li>
          </ul>
        </div>
        
        <div className="admin-link-section">
          <Link to="/admin/login" className="admin-link">管理员后台</Link>
        </div>
      </div>
    </div>
  )
}

export default Home
