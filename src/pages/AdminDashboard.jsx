import React, { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import './AdminDashboard.css'

const statusMap = {
  pending: { label: '待审核', color: '#f59e0b' },
  approved: { label: '已通过', color: '#10b981' },
  rejected: { label: '已拒绝', color: '#ef4444' },
  needs_manual_review: { label: '需人工审核', color: '#6366f1' }
}

const AdminDashboard = ({ token, onLogout }) => {
  const [stats, setStats] = useState(null)
  const [urls, setUrls] = useState([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [pageSize, setPageSize] = useState(20)
  const [search, setSearch] = useState('')
  const [filterStatus, setFilterStatus] = useState('')
  const [loading, setLoading] = useState(false)
  const [selectedUrl, setSelectedUrl] = useState(null)
  const [showReviewModal, setShowReviewModal] = useState(false)
  const [showAIReviewModal, setShowAIReviewModal] = useState(false)
  const [reviewStatus, setReviewStatus] = useState('approved')
  const [reviewComment, setReviewComment] = useState('')
  const [aiConfig, setAIConfig] = useState({
    base_url: '',
    api_key: '',
    model: 'gpt-3.5-turbo'
  })
  const [aiReviewing, setAIReviewing] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const navigate = useNavigate()

  const fetchStats = async () => {
    try {
      const response = await fetch('/api/admin/stats', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      if (response.ok) {
        const data = await response.json()
        setStats(data)
      }
    } catch (err) {
      console.error('获取统计数据失败:', err)
    }
  }

  const fetchUrls = async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams({
        page: page,
        page_size: pageSize
      })
      if (search) params.append('search', search)
      if (filterStatus) params.append('review_status', filterStatus)

      const response = await fetch(`/api/admin/urls?${params}`, {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      
      if (response.status === 401) {
        onLogout()
        navigate('/admin/login')
        return
      }
      
      if (response.ok) {
        const data = await response.json()
        setUrls(data.items)
        setTotal(data.total)
      }
    } catch (err) {
      console.error('获取URL列表失败:', err)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchStats()
    fetchUrls()
  }, [page, pageSize, filterStatus])

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    fetchUrls()
  }

  const handleManualReview = async () => {
    setError('')
    try {
      const response = await fetch('/api/admin/urls/review', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          short_code: selectedUrl.short_code,
          status: reviewStatus,
          comment: reviewComment
        })
      })
      
      if (response.ok) {
        setMessage('审核成功')
        setShowReviewModal(false)
        fetchStats()
        fetchUrls()
        setTimeout(() => setMessage(''), 3000)
      } else {
        const data = await response.json()
        setError(data.detail || '审核失败')
      }
    } catch (err) {
      setError('审核失败: ' + err.message)
    }
  }

  const handleAIReview = async () => {
    setError('')
    setAIReviewing(true)
    try {
      const response = await fetch('/api/admin/urls/ai-review', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          short_code: selectedUrl.short_code,
          ...aiConfig
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setMessage(`AI审核完成: ${statusMap[data.status]?.label || data.status}`)
        setShowAIReviewModal(false)
        fetchStats()
        fetchUrls()
        setTimeout(() => setMessage(''), 5000)
      } else {
        const data = await response.json()
        setError(data.detail || 'AI审核失败')
      }
    } catch (err) {
      setError('AI审核失败: ' + err.message)
    } finally {
      setAIReviewing(false)
    }
  }

  const openReviewModal = (url) => {
    setSelectedUrl(url)
    setReviewStatus(url.review_status || 'approved')
    setReviewComment(url.review_comment || '')
    setShowReviewModal(true)
  }

  const openAIReviewModal = (url) => {
    setSelectedUrl(url)
    setShowAIReviewModal(true)
  }

  const totalPages = Math.ceil(total / pageSize)

  return (
    <div className="admin-container">
      <header className="admin-header">
        <div className="header-content">
          <h1 className="admin-title">管理员后台</h1>
          <div className="header-actions">
            <button className="btn btn-secondary" onClick={onLogout}>退出登录</button>
          </div>
        </div>
      </header>

      <main className="admin-main">
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

        {stats && (
          <div className="stats-grid">
            <div className="stat-card">
              <div className="stat-value">{stats.total_urls.toLocaleString()}</div>
              <div className="stat-label">总URL数</div>
            </div>
            <div className="stat-card stat-pending">
              <div className="stat-value">{stats.pending_review.toLocaleString()}</div>
              <div className="stat-label">待审核</div>
            </div>
            <div className="stat-card stat-approved">
              <div className="stat-value">{stats.approved.toLocaleString()}</div>
              <div className="stat-label">已通过</div>
            </div>
            <div className="stat-card stat-rejected">
              <div className="stat-value">{stats.rejected.toLocaleString()}</div>
              <div className="stat-label">已拒绝</div>
            </div>
            <div className="stat-card stat-needs-review">
              <div className="stat-value">{stats.needs_manual_review.toLocaleString()}</div>
              <div className="stat-label">需人工审核</div>
            </div>
            <div className="stat-card">
              <div className="stat-value">{stats.total_accesses.toLocaleString()}</div>
              <div className="stat-label">总访问次数</div>
            </div>
          </div>
        )}

        <div className="filter-section">
          <form className="search-form" onSubmit={handleSearch}>
            <input
              type="text"
              className="search-input"
              placeholder="搜索短码或URL..."
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
            <button type="submit" className="btn btn-primary">搜索</button>
          </form>
          
          <div className="filter-controls">
            <select
              className="filter-select"
              value={filterStatus}
              onChange={(e) => {
                setFilterStatus(e.target.value)
                setPage(1)
              }}
            >
              <option value="">全部状态</option>
              <option value="pending">待审核</option>
              <option value="approved">已通过</option>
              <option value="rejected">已拒绝</option>
              <option value="needs_manual_review">需人工审核</option>
            </select>
            
            <select
              className="filter-select"
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value))
                setPage(1)
              }}
            >
              <option value={10}>10条/页</option>
              <option value={20}>20条/页</option>
              <option value={50}>50条/页</option>
              <option value={100}>100条/页</option>
            </select>
          </div>
        </div>

        <div className="table-container">
          <table className="url-table">
            <thead>
              <tr>
                <th>短码</th>
                <th>原始URL</th>
                <th>访问次数</th>
                <th>审核状态</th>
                <th>创建时间</th>
                <th>最后访问</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan="7" className="loading-cell">加载中...</td>
                </tr>
              ) : urls.length === 0 ? (
                <tr>
                  <td colSpan="7" className="empty-cell">暂无数据</td>
                </tr>
              ) : (
                urls.map((url) => (
                  <tr key={url.short_code}>
                    <td>
                      <code className="short-code">{url.short_code}</code>
                    </td>
                    <td className="url-cell">
                      <a href={url.original_url} target="_blank" rel="noopener noreferrer" className="url-link">
                        {url.original_url}
                      </a>
                    </td>
                    <td className="number-cell">{url.access_count.toLocaleString()}</td>
                    <td>
                      <span 
                        className="status-badge"
                        style={{ backgroundColor: statusMap[url.review_status]?.color || '#6b7280' }}
                      >
                        {statusMap[url.review_status]?.label || url.review_status}
                      </span>
                    </td>
                    <td className="date-cell">
                      {new Date(url.created_at).toLocaleString()}
                    </td>
                    <td className="date-cell">
                      {new Date(url.last_accessed_at).toLocaleString()}
                    </td>
                    <td className="action-cell">
                      <button 
                        className="btn btn-sm btn-primary"
                        onClick={() => openReviewModal(url)}
                      >
                        人工审核
                      </button>
                      <button 
                        className="btn btn-sm btn-secondary"
                        onClick={() => openAIReviewModal(url)}
                      >
                        AI审核
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>

        {totalPages > 1 && (
          <div className="pagination">
            <button 
              className="btn btn-sm"
              disabled={page === 1}
              onClick={() => setPage(p => p - 1)}
            >
              上一页
            </button>
            <span className="page-info">第 {page} / {totalPages} 页</span>
            <button 
              className="btn btn-sm"
              disabled={page === totalPages}
              onClick={() => setPage(p => p + 1)}
            >
              下一页
            </button>
          </div>
        )}
      </main>

      {showReviewModal && selectedUrl && (
        <div className="modal-overlay">
          <div className="modal">
            <div className="modal-header">
              <h2>人工审核</h2>
              <button className="close-btn" onClick={() => setShowReviewModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="review-info">
                <p><strong>短码:</strong> <code>{selectedUrl.short_code}</code></p>
                <p><strong>URL:</strong> <a href={selectedUrl.original_url} target="_blank" rel="noopener noreferrer">{selectedUrl.original_url}</a></p>
                <p><strong>当前状态:</strong> 
                  <span 
                    className="status-badge"
                    style={{ backgroundColor: statusMap[selectedUrl.review_status]?.color || '#6b7280' }}
                  >
                    {statusMap[selectedUrl.review_status]?.label || selectedUrl.review_status}
                  </span>
                </p>
                {selectedUrl.review_comment && (
                  <p><strong>原有审核意见:</strong> {selectedUrl.review_comment}</p>
                )}
              </div>
              
              <div className="form-group">
                <label>审核状态</label>
                <select 
                  className="form-input"
                  value={reviewStatus}
                  onChange={(e) => setReviewStatus(e.target.value)}
                >
                  <option value="approved">通过</option>
                  <option value="rejected">拒绝</option>
                  <option value="needs_manual_review">需人工审核</option>
                  <option value="pending">待审核</option>
                </select>
              </div>
              
              <div className="form-group">
                <label>审核意见</label>
                <textarea
                  className="form-input"
                  rows="4"
                  value={reviewComment}
                  onChange={(e) => setReviewComment(e.target.value)}
                  placeholder="请输入审核意见（可选）"
                />
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowReviewModal(false)}>取消</button>
              <button className="btn btn-primary" onClick={handleManualReview}>确认审核</button>
            </div>
          </div>
        </div>
      )}

      {showAIReviewModal && selectedUrl && (
        <div className="modal-overlay">
          <div className="modal modal-large">
            <div className="modal-header">
              <h2>AI审核</h2>
              <button className="close-btn" onClick={() => setShowAIReviewModal(false)}>×</button>
            </div>
            <div className="modal-body">
              <div className="review-info">
                <p><strong>短码:</strong> <code>{selectedUrl.short_code}</code></p>
                <p><strong>URL:</strong> <a href={selectedUrl.original_url} target="_blank" rel="noopener noreferrer">{selectedUrl.original_url}</a></p>
              </div>
              
              <div className="ai-config-section">
                <h3>AI接口配置</h3>
                <div className="form-group">
                  <label>API Base URL</label>
                  <input
                    type="text"
                    className="form-input"
                    value={aiConfig.base_url}
                    onChange={(e) => setAIConfig(c => ({ ...c, base_url: e.target.value }))}
                    placeholder="例如: https://api.openai.com"
                  />
                </div>
                <div className="form-group">
                  <label>API Key</label>
                  <input
                    type="password"
                    className="form-input"
                    value={aiConfig.api_key}
                    onChange={(e) => setAIConfig(c => ({ ...c, api_key: e.target.value }))}
                    placeholder="请输入API密钥"
                  />
                </div>
                <div className="form-group">
                  <label>Model</label>
                  <input
                    type="text"
                    className="form-input"
                    value={aiConfig.model}
                    onChange={(e) => setAIConfig(c => ({ ...c, model: e.target.value }))}
                    placeholder="例如: gpt-3.5-turbo"
                  />
                </div>
              </div>
              
              <div className="tips-section">
                <h4>提示:</h4>
                <ul>
                  <li>支持 OpenAI 兼容的接口格式</li>
                  <li>API密钥仅在当前审核请求中使用，不会被存储</li>
                  <li>支持主流AI服务（如OpenAI、Azure OpenAI等）</li>
                </ul>
              </div>
            </div>
            <div className="modal-footer">
              <button className="btn btn-secondary" onClick={() => setShowAIReviewModal(false)}>取消</button>
              <button 
                className="btn btn-primary" 
                onClick={handleAIReview}
                disabled={aiReviewing || !aiConfig.base_url || !aiConfig.api_key || !aiConfig.model}
              >
                {aiReviewing ? 'AI审核中...' : '开始AI审核'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminDashboard
