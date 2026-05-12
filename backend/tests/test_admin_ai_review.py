import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from backend.app.models.url import URLMapping
from backend.app.models.ai_config import AIConfig


@pytest.fixture
def auth_token():
    from backend.app.utils.auth import create_access_token
    return create_access_token(data={"sub": "admin"})


class TestAdminAIReview:
    def test_ai_review_url_success_approved(self, client, test_db_session, auth_token):
        url_mapping = URLMapping(short_code="abc123", original_url="https://example.com")
        test_db_session.add(url_mapping)
        test_db_session.commit()

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

            response = client.post(
                "/admin/urls/ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_code": "abc123",
                    "base_url": "https://api.openai.com",
                    "api_key": "test-key",
                    "model": "gpt-4"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "approved"
        assert data["comment"] == "URL内容合规"

        updated = test_db_session.query(URLMapping).filter(URLMapping.short_code == "abc123").first()
        assert updated.review_status == "approved"
        assert updated.review_comment == "URL内容合规"
        assert updated.reviewed_at is not None

    def test_ai_review_url_success_rejected(self, client, test_db_session, auth_token):
        url_mapping = URLMapping(short_code="def456", original_url="https://malicious.com")
        test_db_session.add(url_mapping)
        test_db_session.commit()

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

            response = client.post(
                "/admin/urls/ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_code": "def456",
                    "base_url": "https://api.openai.com",
                    "api_key": "test-key",
                    "model": "gpt-4"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"

    def test_ai_review_url_not_found(self, client, auth_token):
        response = client.post(
            "/admin/urls/ai-review",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "short_code": "nonexist",
                "base_url": "https://api.openai.com",
                "api_key": "test-key",
                "model": "gpt-4"
            }
        )

        assert response.status_code == 404

    def test_ai_review_url_http_error(self, client, test_db_session, auth_token):
        url_mapping = URLMapping(short_code="ghi789", original_url="https://example.com")
        test_db_session.add(url_mapping)
        test_db_session.commit()

        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.json.return_value = {}

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            response = client.post(
                "/admin/urls/ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_code": "ghi789",
                    "base_url": "https://api.openai.com",
                    "api_key": "test-key",
                    "model": "gpt-4"
                }
            )

        assert response.status_code == 500

    def test_ai_review_url_unauthorized(self, client):
        response = client.post(
            "/admin/urls/ai-review",
            json={
                "short_code": "abc123",
                "base_url": "https://api.openai.com",
                "api_key": "test-key",
                "model": "gpt-4"
            }
        )

        assert response.status_code == 401


class TestAdminBatchAIReview:
    def test_batch_ai_review_success(self, client, test_db_session, auth_token):
        urls = [
            URLMapping(short_code="abc123", original_url="https://example1.com"),
            URLMapping(short_code="def456", original_url="https://example2.com"),
            URLMapping(short_code="ghi789", original_url="https://example3.com"),
        ]
        test_db_session.add_all(urls)
        
        ai_config = AIConfig(
            id="default",
            base_url="https://api.openai.com",
            api_key="test-key",
            model="gpt-4"
        )
        test_db_session.add(ai_config)
        test_db_session.commit()

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

            response = client.post(
                "/admin/urls/batch-ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_codes": ["abc123", "def456", "ghi789"]
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["success"] == 3
        assert data["failed"] == 0

    def test_batch_ai_review_with_failure(self, client, test_db_session, auth_token):
        urls = [
            URLMapping(short_code="abc123", original_url="https://example1.com"),
            URLMapping(short_code="def456", original_url="https://example2.com"),
        ]
        test_db_session.add_all(urls)
        
        ai_config = AIConfig(
            id="default",
            base_url="https://api.openai.com",
            api_key="test-key",
            model="gpt-4"
        )
        test_db_session.add(ai_config)
        test_db_session.commit()

        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "approved", "comment": "URL内容合规"}'
                    }
                }
            ]
        }

        mock_response_error = MagicMock()
        mock_response_error.status_code = 500
        mock_response_error.json.return_value = {}

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=[mock_response_ok, mock_response_error])
            mock_client.return_value.__aenter__.return_value.post = mock_post

            response = client.post(
                "/admin/urls/batch-ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_codes": ["abc123", "nonexist", "def456"]
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["total"] == 3
        assert data["success"] == 1
        assert data["failed"] == 2

    def test_batch_ai_review_no_config(self, client, test_db_session, auth_token):
        response = client.post(
            "/admin/urls/batch-ai-review",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "short_codes": ["abc123"]
            }
        )

        assert response.status_code == 400

    def test_batch_ai_review_unauthorized(self, client):
        response = client.post(
            "/admin/urls/batch-ai-review",
            json={
                "short_codes": ["abc123"]
            }
        )

        assert response.status_code == 401


class TestAIConfigEndpoint:
    def test_save_ai_config_success(self, client, auth_token):
        response = client.post(
            "/admin/ai-config",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "base_url": "https://api.openai.com",
                "api_key": "test-key",
                "model": "gpt-4"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["base_url"] == "https://api.openai.com"
        assert data["model"] == "gpt-4"

    def test_update_ai_config(self, client, test_db_session, auth_token):
        ai_config = AIConfig(
            id="default",
            base_url="https://old.api.com",
            api_key="old-key",
            model="gpt-3.5"
        )
        test_db_session.add(ai_config)
        test_db_session.commit()

        response = client.post(
            "/admin/ai-config",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "base_url": "https://new.api.com",
                "api_key": "new-key",
                "model": "gpt-4"
            }
        )

        assert response.status_code == 200
        data = response.json()
        assert data["base_url"] == "https://new.api.com"
        assert data["model"] == "gpt-4"

    def test_get_ai_config_success(self, client, test_db_session, auth_token):
        ai_config = AIConfig(
            id="default",
            base_url="https://api.openai.com",
            api_key="test-key",
            model="gpt-4"
        )
        test_db_session.add(ai_config)
        test_db_session.commit()

        response = client.get(
            "/admin/ai-config",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["base_url"] == "https://api.openai.com"
        assert data["model"] == "gpt-4"

    def test_get_ai_config_not_found(self, client, auth_token):
        response = client.get(
            "/admin/ai-config",
            headers={"Authorization": f"Bearer {auth_token}"}
        )

        assert response.status_code == 404

    def test_ai_review_with_comment_contains_keyword_but_not_error(self, client, test_db_session, auth_token):
        """
        测试：当AI审核评论中包含类似'失败'的关键词但是正常审核结果时，不应该被判定为服务错误
        """
        url_mapping = URLMapping(short_code="test123", original_url="https://example.com")
        test_db_session.add(url_mapping)
        test_db_session.commit()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "rejected", "comment": "该URL包含违规内容，访问失败风险较高"}'
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            response = client.post(
                "/admin/urls/ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_code": "test123",
                    "base_url": "https://api.openai.com",
                    "api_key": "test-key",
                    "model": "gpt-4"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "rejected"
        assert "该URL包含违规内容" in data["comment"]

    def test_ai_review_with_needs_manual_status(self, client, test_db_session, auth_token):
        """
        测试：当AI返回需要人工审核时，应该正常返回，不应该被判定为服务错误
        """
        url_mapping = URLMapping(short_code="test456", original_url="https://example.com")
        test_db_session.add(url_mapping)
        test_db_session.commit()

        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "needs_manual_review", "comment": "无法明确判断，需要人工审核"}'
                    }
                }
            ]
        }

        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post

            response = client.post(
                "/admin/urls/ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_code": "test456",
                    "base_url": "https://api.openai.com",
                    "api_key": "test-key",
                    "model": "gpt-4"
                }
            )

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "needs_manual_review"
