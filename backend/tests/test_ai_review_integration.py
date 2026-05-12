import pytest
from unittest.mock import AsyncMock, patch, MagicMock
import logging


@pytest.fixture
def auth_token():
    from backend.app.utils.auth import create_access_token
    return create_access_token(data={"sub": "admin"})


@pytest.fixture(autouse=True)
def setup_test_logging():
    logging.basicConfig(level=logging.DEBUG)


class TestAIReviewIntegration:
    def test_full_ai_review_workflow_success(self, client, test_db_session, auth_token):
        test_url = "https://example.com/test-page"
        
        url_data = {
            "url": test_url
        }
        create_response = client.post("/shorten", json=url_data)
        assert create_response.status_code == 200
        short_code = create_response.json()["short_code"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "approved", "comment": "URL内容合规，符合安全标准"}'
                    }
                }
            ]
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            review_response = client.post(
                "/admin/urls/ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_code": short_code,
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "test-api-key-12345",
                    "model": "gpt-4"
                }
            )
        
        assert review_response.status_code == 200
        result = review_response.json()
        assert result["status"] == "approved"
        assert "URL内容合规" in result["comment"]
        
        get_response = client.get(f"/admin/urls?page=1&page_size=10",
                                  headers={"Authorization": f"Bearer {auth_token}"})
        assert get_response.status_code == 200
        
        url_list = get_response.json()["items"]
        reviewed_url = next((u for u in url_list if u["short_code"] == short_code), None)
        assert reviewed_url is not None
        assert reviewed_url["review_status"] == "approved"
        assert "URL内容合规" in reviewed_url["review_comment"]

    def test_ai_review_workflow_rejected(self, client, test_db_session, auth_token):
        url_data = {"url": "https://malicious-example.com"}
        create_response = client.post("/shorten", json=url_data)
        short_code = create_response.json()["short_code"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "rejected", "comment": "检测到恶意内容，URL包含欺诈信息"}'
                    }
                }
            ]
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            review_response = client.post(
                "/admin/urls/ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_code": short_code,
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "test-api-key-12345",
                    "model": "gpt-4"
                }
            )
        
        assert review_response.status_code == 200
        result = review_response.json()
        assert result["status"] == "rejected"

    def test_ai_review_workflow_invalid_api_key(self, client, test_db_session, auth_token):
        url_data = {"url": "https://example.com"}
        create_response = client.post("/shorten", json=url_data)
        short_code = create_response.json()["short_code"]
        
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.text = '{"error": {"message": "Invalid API key"}}'
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            review_response = client.post(
                "/admin/urls/ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_code": short_code,
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "test-api-key-12345",
                    "model": "gpt-4"
                }
            )
        
        assert review_response.status_code == 500
        assert "认证失败" in review_response.json()["detail"]

    def test_ai_review_workflow_invalid_url_short_code(self, client, auth_token):
        review_response = client.post(
            "/admin/urls/ai-review",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "short_code": "nonexistent-code-12345",
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-api-key-12345",
                "model": "gpt-4"
            }
        )
        
        assert review_response.status_code == 404
        assert "短码不存在" in review_response.json()["detail"]

    def test_ai_review_workflow_malformed_ai_response(self, client, test_db_session, auth_token):
        url_data = {"url": "https://example.com"}
        create_response = client.post("/shorten", json=url_data)
        short_code = create_response.json()["short_code"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": "This is plain text response without proper JSON format"
                    }
                }
            ]
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            review_response = client.post(
                "/admin/urls/ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_code": short_code,
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "test-api-key-12345",
                    "model": "gpt-4"
                }
            )
        
        assert review_response.status_code == 200
        result = review_response.json()
        assert result["status"] == "needs_manual_review"
        assert "JSON" in result["comment"]

    def test_ai_review_workflow_missing_choices(self, client, test_db_session, auth_token):
        url_data = {"url": "https://example.com"}
        create_response = client.post("/shorten", json=url_data)
        short_code = create_response.json()["short_code"]
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "data": [],
            "other_field": "something"
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            review_response = client.post(
                "/admin/urls/ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_code": short_code,
                    "base_url": "https://api.openai.com/v1",
                    "api_key": "test-api-key-12345",
                    "model": "gpt-4"
                }
            )
        
        assert review_response.status_code == 500
        assert "choices" in review_response.json()["detail"]


class TestBatchAIReviewIntegration:
    def test_batch_ai_review_workflow(self, client, test_db_session, auth_token):
        config_response = client.post(
            "/admin/ai-config",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-api-key-12345",
                "model": "gpt-4"
            }
        )
        assert config_response.status_code == 200
        
        short_codes = []
        for i in range(3):
            url_data = {"url": f"https://example{i}.com"}
            create_response = client.post("/shorten", json=url_data)
            short_codes.append(create_response.json()["short_code"])
        
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "approved", "comment": "内容合规"}'
                    }
                }
            ]
        }
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(return_value=mock_response)
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            batch_response = client.post(
                "/admin/urls/batch-ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_codes": short_codes
                }
            )
        
        assert batch_response.status_code == 200
        result = batch_response.json()
        assert result["total"] == 3
        assert result["success"] == 3
        assert result["failed"] == 0

    def test_batch_ai_review_with_mixed_results(self, client, test_db_session, auth_token):
        config_response = client.post(
            "/admin/ai-config",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-api-key-12345",
                "model": "gpt-4"
            }
        )
        
        short_codes = []
        for i in range(2):
            url_data = {"url": f"https://example{i}.com"}
            create_response = client.post("/shorten", json=url_data)
            short_codes.append(create_response.json()["short_code"])
        
        mock_response_ok = MagicMock()
        mock_response_ok.status_code = 200
        mock_response_ok.json.return_value = {
            "choices": [
                {
                    "message": {
                        "content": '{"status": "approved", "comment": "内容合规"}'
                    }
                }
            ]
        }
        
        mock_response_error = MagicMock()
        mock_response_error.status_code = 500
        mock_response_error.text = ""
        
        with patch("httpx.AsyncClient") as mock_client:
            mock_post = AsyncMock(side_effect=[mock_response_ok, mock_response_error])
            mock_client.return_value.__aenter__.return_value.post = mock_post
            
            batch_response = client.post(
                "/admin/urls/batch-ai-review",
                headers={"Authorization": f"Bearer {auth_token}"},
                json={
                    "short_codes": short_codes + ["nonexistent"]
                }
            )
        
        assert batch_response.status_code == 200
        result = batch_response.json()
        assert result["total"] == 3
        assert result["success"] == 1
        assert result["failed"] == 2

    def test_batch_ai_review_no_config(self, client, auth_token):
        batch_response = client.post(
            "/admin/urls/batch-ai-review",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "short_codes": ["test1", "test2"]
            }
        )
        
        assert batch_response.status_code == 400
        assert "请先配置AI设置" in batch_response.json()["detail"]


class TestAIConfigIntegration:
    def test_ai_config_full_workflow(self, client, auth_token):
        config_response = client.post(
            "/admin/ai-config",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "base_url": "https://api.openai.com/v1",
                "api_key": "test-api-key-12345",
                "model": "gpt-4"
            }
        )
        assert config_response.status_code == 200
        config = config_response.json()
        assert config["base_url"] == "https://api.openai.com/v1"
        assert config["model"] == "gpt-4"
        
        get_response = client.get(
            "/admin/ai-config",
            headers={"Authorization": f"Bearer {auth_token}"}
        )
        assert get_response.status_code == 200
        retrieved_config = get_response.json()
        assert retrieved_config["base_url"] == "https://api.openai.com/v1"
        
        update_response = client.post(
            "/admin/ai-config",
            headers={"Authorization": f"Bearer {auth_token}"},
            json={
                "base_url": "https://api.anthropic.com/v1",
                "api_key": "new-api-key-67890",
                "model": "claude-3"
            }
        )
        assert update_response.status_code == 200
        updated_config = update_response.json()
        assert updated_config["base_url"] == "https://api.anthropic.com/v1"
        assert updated_config["model"] == "claude-3"
