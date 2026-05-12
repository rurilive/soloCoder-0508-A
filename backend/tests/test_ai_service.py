import pytest
import json
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from backend.app.services.ai_service import (
    review_url_with_ai,
    AIConfig,
    ReviewResult,
    _normalize_base_url,
    _build_prompt,
    _build_request_payload,
    _parse_ai_response,
    _handle_http_error
)


class TestAIServiceHelpers:
    def test_normalize_base_url(self):
        assert _normalize_base_url("https://api.openai.com") == "https://api.openai.com/v1"
        assert _normalize_base_url("https://api.openai.com/") == "https://api.openai.com/v1"
        assert _normalize_base_url("https://api.openai.com/v1") == "https://api.openai.com/v1"
        assert _normalize_base_url("https://api.openai.com/v1/") == "https://api.openai.com/v1"

    def test_build_prompt_contains_url(self):
        prompt = _build_prompt("https://example.com")
        assert "https://example.com" in prompt
        assert "approved" in prompt
        assert "rejected" in prompt
        assert "needs_manual_review" in prompt

    def test_build_request_payload(self):
        payload = _build_request_payload("gpt-4", "test prompt")
        assert payload["model"] == "gpt-4"
        assert len(payload["messages"]) == 2
        assert payload["temperature"] == 0.1
        assert payload["max_tokens"] == 500

    def test_parse_ai_response_approved(self):
        content = '{"status": "approved", "comment": "内容合规"}'
        result = _parse_ai_response(content)
        assert result.status == "approved"
        assert result.comment == "内容合规"

    def test_parse_ai_response_rejected(self):
        content = '{"status": "rejected", "comment": "包含违规内容"}'
        result = _parse_ai_response(content)
        assert result.status == "rejected"

    def test_parse_ai_response_needs_manual(self):
        content = '{"status": "needs_manual_review", "comment": "需要人工审核"}'
        result = _parse_ai_response(content)
        assert result.status == "needs_manual_review"

    def test_parse_ai_response_with_markdown_json_valid(self):
        content = '''```json
{"status": "approved", "comment": "内容合规"}
```'''
        result = _parse_ai_response(content)
        assert result.status == "approved"

    def test_parse_ai_response_invalid_json(self):
        content = "This is not JSON at all"
        result = _parse_ai_response(content)
        assert result.status == "needs_manual_review"
        assert "未找到有效的JSON对象" in result.comment

    def test_parse_ai_response_json_decode_error(self):
        content = '{invalid json}'
        result = _parse_ai_response(content)
        assert result.status == "needs_manual_review"
        assert "JSON解析错误" in result.comment

    def test_parse_ai_response_invalid_status(self):
        content = '{"status": "unknown_status", "comment": "test"}'
        result = _parse_ai_response(content)
        assert result.status == "needs_manual_review"
        assert "无效的审核状态" in result.comment

    def test_handle_http_error_401(self):
        result = _handle_http_error(401, "")
        assert "认证失败" in result.comment

    def test_handle_http_error_404(self):
        result = _handle_http_error(404, "")
        assert "端点不存在" in result.comment

    def test_handle_http_error_429(self):
        result = _handle_http_error(429, "")
        assert "请求过于频繁" in result.comment

    def test_handle_http_error_500(self):
        result = _handle_http_error(500, "")
        assert "内部错误" in result.comment

    def test_handle_http_error_with_error_message(self):
        response_text = '{"error": {"message": "Invalid API key"}}'
        result = _handle_http_error(401, response_text)
        assert "Invalid API key" in result.comment


class TestAIService:
    @pytest.fixture
    def sample_config(self):
        return AIConfig(
            base_url="https://api.openai.com",
            api_key="test-key",
            model="gpt-4"
        )

    @pytest.mark.asyncio
    async def test_review_url_with_ai_success_approved(self, sample_config):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "approved", "comment": "URL内容合规"}'
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert isinstance(result, ReviewResult)
            assert result.status == "approved"
            assert result.comment == "URL内容合规"

    @pytest.mark.asyncio
    async def test_review_url_with_ai_success_rejected(self, sample_config):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "rejected", "comment": "包含违规内容"}'
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://malicious.com", sample_config)

            assert result.status == "rejected"
            assert result.comment == "包含违规内容"

    @pytest.mark.asyncio
    async def test_review_url_with_ai_success_needs_manual(self, sample_config):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "needs_manual_review", "comment": "无法确定"}'
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://uncertain.com", sample_config)

            assert result.status == "needs_manual_review"
            assert result.comment == "无法确定"

    @pytest.mark.asyncio
    async def test_review_url_with_ai_empty_url_empty(self, sample_config):
        result = await review_url_with_ai("", sample_config)
        assert result.status == "needs_manual_review"
        assert "URL为空" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_invalid_config(self):
        config = AIConfig(base_url="", api_key="", model="")
        result = await review_url_with_ai("https://example.com", config)
        assert result.status == "needs_manual_review"
        assert "配置不完整" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_invalid_json_response(self, sample_config):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This is not a valid JSON response"
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "AI返回格式不正确" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_invalid_status(self, sample_config):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "invalid_status", "comment": "test"}'
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "无效的审核状态" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_http_401_error(self, sample_config):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = ""

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "认证失败" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_http_404_error(self, sample_config):
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = ""

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "端点不存在" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_connect_error(self, sample_config):
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=httpx.ConnectError("Connection refused"))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "连接失败" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_timeout(self, sample_config):
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "请求超时" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_too_many_redirects(self, sample_config):
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=httpx.TooManyRedirects("Too many redirects"))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "重定向次数过多" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_missing_choices_field(self, sample_config):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {}

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "缺少或无效的'choices'字段" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_missing_content_field(self, sample_config):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {}
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "缺少'message.content'字段" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_invalid_json_in_response(self, sample_config):
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "无效的JSON响应" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_general_exception(self, sample_config):
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "发生未知错误" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_base_url_with_v1(self, sample_config):
        config = AIConfig(
            base_url="https://api.openai.com/v1",
            api_key="test-key",
            model="gpt-4"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "approved", "comment": "OK"}'
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            await review_url_with_ai("https://example.com", config)

            call_args = mock_post.call_args
            assert call_args is not None
            assert "https://api.openai.com/v1/chat/completions" in call_args[0]

    @pytest.mark.asyncio
    async def test_review_url_with_ai_base_url_without_v1(self, sample_config):
        config = AIConfig(
            base_url="https://api.openai.com/",
            api_key="test-key",
            model="gpt-4"
        )

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "approved", "comment": "OK"}'
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            await review_url_with_ai("https://example.com", config)

            call_args = mock_post.call_args
            assert call_args is not None
            assert "https://api.openai.com/v1/chat/completions" in call_args[0]
