import pytest


class TestRootEndpoint:
    def test_root_returns_service_info(self, client):
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert "service" in data
        assert "strategy" in data
        assert "short_code_pool" in data
        assert "endpoints" in data

    def test_root_stats_structure(self, client, sample_url_mappings):
        response = client.get("/")
        data = response.json()
        pool = data["short_code_pool"]
        assert "total_pool" in pool
        assert "used_count" in pool
        assert pool["used_count"] == 3


class TestStatsEndpoint:
    def test_stats_endpoint_structure(self, client, sample_url_mappings):
        response = client.get("/stats")
        assert response.status_code == 200
        data = response.json()
        expected_keys = [
            "total_pool", "used_count", "available_count",
            "usage_percent", "oldest_accessed", "newest_accessed"
        ]
        for key in expected_keys:
            assert key in data

    def test_stats_empty_database(self, client):
        response = client.get("/stats")
        data = response.json()
        assert data["used_count"] == 0
        assert data["oldest_accessed"] is None
        assert data["newest_accessed"] is None


class TestShortenEndpoint:
    def test_post_shorten_success(self, client):
        response = client.post("/shorten", json={"url": "https://test.example.com"})
        assert response.status_code == 200
        data = response.json()
        assert "short_code" in data
        assert data["original_url"] == "https://test.example.com"
        assert data["is_reused"] is False
        assert data["replaced_url"] is None

    def test_post_shorten_duplicate_url(self, client):
        url = "https://duplicate.com"
        response1 = client.post("/shorten", json={"url": url})
        data1 = response1.json()
        response2 = client.post("/shorten", json={"url": url})
        data2 = response2.json()
        assert data1["short_code"] == data2["short_code"]
        assert data2["is_reused"] is False

    def test_post_shorten_missing_url(self, client):
        response = client.post("/shorten", json={})
        assert response.status_code == 422

    def test_post_shorten_invalid_payload(self, client):
        response = client.post("/shorten", json={"url": 123})
        assert response.status_code == 422

    def test_post_shorten_response_model(self, client):
        response = client.post("/shorten", json={"url": "https://api-test.com"})
        data = response.json()
        assert isinstance(data["short_code"], str)
        assert len(data["short_code"]) == 6
        assert isinstance(data["original_url"], str)
        assert isinstance(data["is_reused"], bool)


class TestRedirectEndpoint:
    def test_redirect_existing_short_code(self, client, sample_url_mappings):
        response = client.get("/abc123", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == "https://example.com"

    def test_redirect_nonexistent_short_code(self, client):
        response = client.get("/nonexist")
        assert response.status_code == 404
        assert "detail" in response.json()

    def test_redirect_updates_access_time(self, client, test_db_session, sample_url_mappings):
        from backend.app.models.url import URLMapping
        mapping = test_db_session.query(URLMapping).filter_by(short_code="def456").first()
        original_time = mapping.last_accessed_at
        client.get("/def456", follow_redirects=False)
        test_db_session.refresh(mapping)
        assert mapping.last_accessed_at > original_time

    def test_redirect_multiple_accesses(self, client, test_db_session, sample_url_mappings):
        from backend.app.models.url import URLMapping
        first = client.get("/ghi789", follow_redirects=False)
        assert first.status_code == 302
        second = client.get("/ghi789", follow_redirects=False)
        assert second.status_code == 302
        mapping = test_db_session.query(URLMapping).filter_by(short_code="ghi789").first()
        assert mapping.last_accessed_at is not None


class TestIntegrationFlow:
    def test_create_then_redirect(self, client):
        original_url = "https://full-flow-test.com"
        shorten_response = client.post("/shorten", json={"url": original_url})
        assert shorten_response.status_code == 200
        short_code = shorten_response.json()["short_code"]
        redirect_response = client.get(f"/{short_code}", follow_redirects=False)
        assert redirect_response.status_code == 302
        assert redirect_response.headers["location"] == original_url

    def test_create_multiple_then_check_stats(self, client):
        urls = [
            "https://integration-1.com",
            "https://integration-2.com",
            "https://integration-3.com",
        ]
        for url in urls:
            client.post("/shorten", json={"url": url})
        stats = client.get("/stats").json()
        assert stats["used_count"] == len(urls)
