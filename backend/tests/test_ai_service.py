import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import httpx

from backend.app.services.ai_service import (
    review_url_with_ai,
    AIConfig,
    ReviewResult
)


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

    @pytest.mark.asyncio
    async def test_review_url_with_ai_http_error(self, sample_config):
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {}

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "AI服务调用失败" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_timeout(self, sample_config):
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=httpx.TimeoutException("Request timed out"))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "AI服务请求超时" in result.comment

    @pytest.mark.asyncio
    async def test_review_url_with_ai_general_exception(self, sample_config):
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=Exception("Unexpected error"))
            mock_client.return_value.__aenter__.return_value.post = mock_post

            result = await review_url_with_ai("https://example.com", sample_config)

            assert result.status == "needs_manual_review"
            assert "AI审核过程中出错" in result.comment

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
