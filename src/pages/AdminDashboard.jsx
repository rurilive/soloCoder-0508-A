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
  const navigate = useNavigate()
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
  const [reviewStatus, setReviewStatus] = useState('approved')
  const [reviewComment, setReviewComment] = useState('')
  const [selectedShortCodes, setSelectedShortCodes] = useState([])
  const [batchReviewing, setBatchReviewing] = useState(false)
  const [aiConfigured, setAiConfigured] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')

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

  const checkAIConfig = async () => {
    try {
      const response = await fetch('/api/admin/ai-config', {
        headers: { 'Authorization': `Bearer ${token}` }
      })
      setAiConfigured(response.ok)
    } catch (err) {
      setAiConfigured(false)
    }
  }

  useEffect(() => {
    fetchStats()
    fetchUrls()
    checkAIConfig()
  }, [page, pageSize, filterStatus])

  const handleSearch = (e) => {
    e.preventDefault()
    setPage(1)
    fetchUrls()
  }

  const handleSelectAll = (e) => {
    if (e.target.checked) {
      setSelectedShortCodes(urls.map(u => u.short_code))
    } else {
      setSelectedShortCodes([])
    }
  }

  const handleSelectOne = (shortCode) => {
    if (selectedShortCodes.includes(shortCode)) {
      setSelectedShortCodes(selectedShortCodes.filter(s => s !== shortCode))
    } else {
      setSelectedShortCodes([...selectedShortCodes, shortCode])
    }
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

  const handleBatchAIReview = async () => {
    if (selectedShortCodes.length === 0) {
      setError('请选择要审核的短码')
      return
    }
    if (!aiConfigured) {
      setError('请先在AI设置页面配置AI接口')
      return
    }
    
    setError('')
    setMessage('')
    setBatchReviewing(true)
    try {
      const response = await fetch('/api/admin/urls/batch-ai-review', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          short_codes: selectedShortCodes
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        
        if (data.failed > 0) {
          const failedItems = data.results.filter(r => r.status === 'failed')
          const errorDetails = failedItems.slice(0, 3).map(r => `${r.short_code}: ${r.error}`).join('; ')
          const moreText = failedItems.length > 3 ? `，还有 ${failedItems.length - 3} 个错误` : ''
          setError(`批量AI审核完成：成功 ${data.success} 个，失败 ${data.failed} 个。错误详情: ${errorDetails}${moreText}`)
        } else {
          setMessage(`批量AI审核完成：成功 ${data.success} 个，失败 ${data.failed} 个`)
        }
        
        setSelectedShortCodes([])
        fetchStats()
        fetchUrls()
        
        if (data.failed === 0) {
          setTimeout(() => setMessage(''), 5000)
        }
      } else {
        const data = await response.json()
        setError(data.detail || '批量审核失败')
      }
    } catch (err) {
      setError('批量审核失败: ' + err.message)
    } finally {
      setBatchReviewing(false)
    }
  }

  const handleBatchManualReview = async () => {
    if (selectedShortCodes.length === 0) {
      setError('请选择要审核的短码')
      return
    }
    
    setError('')
    setBatchReviewing(true)
    try {
      const response = await fetch('/api/admin/urls/batch-review', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
          short_codes: selectedShortCodes,
          status: reviewStatus,
          comment: reviewComment
        })
      })
      
      if (response.ok) {
        const data = await response.json()
        setMessage(`批量审核完成：成功 ${data.success} 个，失败 ${data.failed} 个`)
        setSelectedShortCodes([])
        setShowReviewModal(false)
        fetchStats()
        fetchUrls()
        setTimeout(() => setMessage(''), 5000)
      } else {
        const data = await response.json()
        setError(data.detail || '批量审核失败')
      }
    } catch (err) {
      setError('批量审核失败: ' + err.message)
    } finally {
      setBatchReviewing(false)
    }
  }

  const openReviewModal = (url) => {
    setSelectedUrl(url)
    setReviewStatus(url.review_status || 'approved')
    setReviewComment(url.review_comment || '')
    setShowReviewModal(true)
  }

  const totalPages = Math.ceil(total / pageSize)
  const allSelected = urls.length > 0 && selectedShortCodes.length === urls.length

  return (
    <div className="admin-container">
      <header className="admin-header">
        <div className="header-content">
          <h1 className="admin-title">管理员后台</h1>
          <div className="header-actions">
            <button 
              className="btn btn-secondary" 
              onClick={() => navigate('/admin/ai-settings')}
            >
              ⚙️ AI 设置
            </button>
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

        {selectedShortCodes.length > 0 && (
          <div className="batch-actions">
            <span>已选择 {selectedShortCodes.length} 项</span>
            <button 
              className="btn btn-primary"
              onClick={handleBatchAIReview}
              disabled={batchReviewing || !aiConfigured}
            >
              {batchReviewing ? 'AI审核中...' : '批量AI审核'}
            </button>
            <button 
              className="btn btn-secondary"
              onClick={() => {
                setReviewStatus('approved')
                setReviewComment('')
                setSelectedUrl({ short_code: 'batch' })
                setShowReviewModal(true)
              }}
            >
              批量人工审核
            </button>
            <button 
              className="btn btn-secondary"
              onClick={() => setSelectedShortCodes([])}
            >
              取消选择
            </button>
          </div>
        )}

        <div className="table-container">
          <table className="url-table">
            <thead>
              <tr>
                <th style={{ width: '40px' }}>
                  <input 
                    type="checkbox" 
                    checked={allSelected}
                    onChange={handleSelectAll}
                  />
                </th>
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
                  <td colSpan="8" className="loading-cell">加载中...</td>
                </tr>
              ) : urls.length === 0 ? (
                <tr>
                  <td colSpan="8" className="empty-cell">暂无数据</td>
                </tr>
              ) : (
                urls.map((url) => (
                  <tr key={url.short_code}>
                    <td>
                      <input 
                        type="checkbox" 
                        checked={selectedShortCodes.includes(url.short_code)}
                        onChange={() => handleSelectOne(url.short_code)}
                      />
                    </td>
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
              <h2>{selectedUrl.short_code === 'batch' ? '批量人工审核' : '人工审核'}</h2>
              <button className="close-btn" onClick={() => setShowReviewModal(false)}>×</button>
            </div>
            <div className="modal-body">
              {selectedUrl.short_code !== 'batch' && (
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
              )}
              
              {selectedUrl.short_code === 'batch' && (
                <div className="review-info">
                  <p><strong>批量审核数量:</strong> {selectedShortCodes.length}</p>
                </div>
              )}
              
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
              {selectedUrl.short_code === 'batch' ? (
                <button 
                  className="btn btn-primary" 
                  onClick={handleBatchManualReview}
                  disabled={batchReviewing}
                >
                  {batchReviewing ? '审核中...' : '确认批量审核'}
                </button>
              ) : (
                <button className="btn btn-primary" onClick={handleManualReview}>确认审核</button>
              )}
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default AdminDashboard
