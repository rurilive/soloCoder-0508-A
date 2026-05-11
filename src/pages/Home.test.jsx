import React from 'react'
import { render, screen, waitFor, fireEvent } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import Home from './Home'

const originalFetch = global.fetch

describe('Home Component', () => {
  beforeEach(() => {
    global.fetch = vi.fn()
    Object.assign(navigator, {
      clipboard: {
        writeText: vi.fn().mockResolvedValueOnce()
      }
    })
  })

  afterEach(() => {
    vi.restoreAllMocks()
    global.fetch = originalFetch
  })

  describe('Initial Render', () => {
    it('renders the title', () => {
      render(<Home />)
      expect(screen.getByText('URL 缩短服务')).toBeInTheDocument()
    })

    it('renders the subtitle', () => {
      render(<Home />)
      expect(screen.getByText('将长链接转换为简洁易分享的短链接')).toBeInTheDocument()
    })

    it('renders the URL input field', () => {
      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      expect(input).toBeInTheDocument()
      expect(input).toHaveAttribute('type', 'url')
      expect(input).toBeRequired()
    })

    it('renders the shorten button', () => {
      render(<Home />)
      expect(screen.getByRole('button', { name: '缩短' })).toBeInTheDocument()
    })

    it('renders the view stats button', () => {
      render(<Home />)
      expect(screen.getByRole('button', { name: '查看统计数据' })).toBeInTheDocument()
    })

    it('renders the usage instructions', () => {
      render(<Home />)
      expect(screen.getByText('使用说明')).toBeInTheDocument()
    })

    it('does not show result card initially', () => {
      render(<Home />)
      expect(screen.queryByText('缩短成功！')).not.toBeInTheDocument()
    })

    it('does not show stats card initially', () => {
      render(<Home />)
      expect(screen.queryByText('短码池统计')).not.toBeInTheDocument()
    })
  })

  describe('URL Input and Submit', () => {
    it('updates input value when typing', () => {
      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      fireEvent.change(input, { target: { value: 'https://example.com' } })
      expect(input.value).toBe('https://example.com')
    })

    it('disables submit button when input is empty', () => {
      render(<Home />)
      const button = screen.getByRole('button', { name: '缩短' })
      expect(button).toBeDisabled()
    })

    it('enables submit button when input has value', () => {
      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      fireEvent.change(input, { target: { value: 'https://example.com' } })
      const button = screen.getByRole('button', { name: '缩短' })
      expect(button).not.toBeDisabled()
    })

    it('shows loading state while submitting', async () => {
      global.fetch.mockImplementation(() =>
        new Promise((resolve) => setTimeout(() => resolve({
          ok: true,
          json: async () => ({ short_code: 'abc123', original_url: 'https://example.com' })
        }), 100))
      )

      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      fireEvent.change(input, { target: { value: 'https://example.com' } })
      const button = screen.getByRole('button', { name: '缩短' })
      fireEvent.click(button)

      await waitFor(() => {
        expect(screen.getByRole('button', { name: '处理中...' })).toBeInTheDocument()
      })
    })

    it('calls API with correct parameters on submit', async () => {
      const url = 'https://test-url.com'
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ short_code: 'xyz789', original_url: url })
      })

      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      fireEvent.change(input, { target: { value: url } })
      fireEvent.click(screen.getByRole('button', { name: '缩短' }))

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith('/api/shorten', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ url })
        })
      })
    })
  })

  describe('Successful URL Shortening', () => {
    it('displays result card after successful shorten', async () => {
      const url = 'https://success-example.com'
      const shortCode = 'abc123'
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ short_code: shortCode, original_url: url, is_reused: false })
      })

      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      fireEvent.change(input, { target: { value: url } })
      fireEvent.click(screen.getByRole('button', { name: '缩短' }))

      await waitFor(() => {
        expect(screen.getByText('缩短成功！')).toBeInTheDocument()
      })

      expect(screen.getByText('原始链接:')).toBeInTheDocument()
      expect(screen.getByText(url)).toBeInTheDocument()
      expect(screen.getByText('短链接:')).toBeInTheDocument()
      expect(screen.getByText(`http://localhost:1111/${shortCode}`)).toBeInTheDocument()
    })

    it('does not show reused warning when is_reused is false', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ short_code: 'test12', original_url: 'https://test.com', is_reused: false })
      })

      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      fireEvent.change(input, { target: { value: 'https://test.com' } })
      fireEvent.click(screen.getByRole('button', { name: '缩短' }))

      await waitFor(() => {
        expect(screen.getByText('缩短成功！')).toBeInTheDocument()
      })

      expect(screen.queryByText(/提示：由于短码池已满/)).not.toBeInTheDocument()
    })

    it('shows reused warning when is_reused is true', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({
          short_code: 'reused',
          original_url: 'https://new-url.com',
          is_reused: true,
          replaced_url: 'https://old-url.com'
        })
      })

      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      fireEvent.change(input, { target: { value: 'https://new-url.com' } })
      fireEvent.click(screen.getByRole('button', { name: '缩短' }))

      await waitFor(() => {
        expect(screen.getByText(/提示：由于短码池已满/)).toBeInTheDocument()
      })
      expect(screen.getByText(/https:\/\/old-url\.com/)).toBeInTheDocument()
    })
  })

  describe('Error Handling', () => {
    it('displays error message on API failure with detail', async () => {
      const errorDetail = 'Invalid URL format'
      global.fetch.mockResolvedValue({
        ok: false,
        json: async () => ({ detail: errorDetail })
      })

      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      fireEvent.change(input, { target: { value: 'https://error.com' } })
      fireEvent.click(screen.getByRole('button', { name: '缩短' }))

      await waitFor(() => {
        expect(screen.getByText(errorDetail)).toBeInTheDocument()
      })
    })

    it('displays generic error when detail is not available', async () => {
      global.fetch.mockResolvedValue({
        ok: false,
        json: async () => ({})
      })

      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      fireEvent.change(input, { target: { value: 'https://generic-error.com' } })
      fireEvent.click(screen.getByRole('button', { name: '缩短' }))

      await waitFor(() => {
        expect(screen.getByText('请求失败')).toBeInTheDocument()
      })
    })

    it('displays error on network failure', async () => {
      global.fetch.mockRejectedValue(new Error('Network error'))

      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      fireEvent.change(input, { target: { value: 'https://network-error.com' } })
      fireEvent.click(screen.getByRole('button', { name: '缩短' }))

      await waitFor(() => {
        expect(screen.getByText('Network error')).toBeInTheDocument()
      })
    })
  })

  describe('Stats Feature', () => {
    it('calls stats API when button is clicked', async () => {
      global.fetch.mockResolvedValue({
        json: async () => ({
          total_pool: 56800235584,
          used_count: 10,
          available_count: 56800235574,
          usage_percent: 0.00002,
          oldest_accessed: '2026-05-11T10:00:00',
          newest_accessed: '2026-05-11T11:00:00'
        })
      })

      render(<Home />)
      fireEvent.click(screen.getByRole('button', { name: '查看统计数据' }))

      await waitFor(() => {
        expect(global.fetch).toHaveBeenCalledWith('/api/stats')
      })
    })

    it('displays stats card with correct values', async () => {
      const statsData = {
        total_pool: 56800235584,
        used_count: 10,
        available_count: 56800235574,
        usage_percent: 0.00002,
        oldest_accessed: '2026-05-01T00:00:00',
        newest_accessed: '2026-05-11T12:00:00'
      }
      global.fetch.mockResolvedValue({
        json: async () => statsData
      })

      render(<Home />)
      fireEvent.click(screen.getByRole('button', { name: '查看统计数据' }))

      await waitFor(() => {
        expect(screen.getByText('短码池统计')).toBeInTheDocument()
      })

      expect(screen.getByText('总容量')).toBeInTheDocument()
      expect(screen.getByText('已使用')).toBeInTheDocument()
      expect(screen.getByText('可用')).toBeInTheDocument()
      expect(screen.getByText('使用率')).toBeInTheDocument()
      expect(screen.getByText('10')).toBeInTheDocument()
      expect(screen.getByText('0.00002%')).toBeInTheDocument()
    })

    it('shows loading state while fetching stats', async () => {
      global.fetch.mockImplementation(() =>
        new Promise((resolve) => setTimeout(() => resolve({
          json: async () => ({})
        }), 100))
      )

      render(<Home />)
      fireEvent.click(screen.getByRole('button', { name: '查看统计数据' }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: '加载中...' })).toBeInTheDocument()
      })
    })
  })

  describe('Copy to Clipboard', () => {
    it('shows copy button in result', async () => {
      global.fetch.mockResolvedValue({
        ok: true,
        json: async () => ({ short_code: 'copy12', original_url: 'https://copy.com', is_reused: false })
      })

      render(<Home />)
      const input = screen.getByPlaceholderText(/请输入要缩短的 URL/)
      fireEvent.change(input, { target: { value: 'https://copy.com' } })
      fireEvent.click(screen.getByRole('button', { name: '缩短' }))

      await waitFor(() => {
        expect(screen.getByRole('button', { name: '复制' })).toBeInTheDocument()
      })
    })
  })
})
