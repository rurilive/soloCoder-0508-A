import pytest
from backend.app.services.url_service import create_short_url


class TestEdgeCasesURLFormat:
    def test_shorten_very_long_url(self, test_db_session):
        long_url = "https://" + "a" * 2000 + ".com/" + "b" * 1000
        response = create_short_url(test_db_session, long_url)
        assert response.short_code is not None
        assert len(response.short_code) == 6
        assert response.original_url == long_url

    def test_shorten_url_with_special_characters(self, test_db_session):
        special_urls = [
            "https://example.com/path?query=value&another=test#fragment",
            "https://user:pass@example.com:8080/path",
            "https://example.com/日本語/中文/한국어",
            "https://example.com/path with spaces",
            "https://example.com/%E4%B8%AD%E6%96%87",
            "https://example.com/path?query=<script>alert(1)</script>",
            "https://example.com/path?query=' OR '1'='1",
        ]
        for url in special_urls:
            response = create_short_url(test_db_session, url)
            assert response.short_code is not None
            assert response.original_url == url

    def test_url_with_minimal_length(self, test_db_session):
        minimal_urls = [
            "https://a.co",
            "http://x.io",
            "https://t.co",
        ]
        for url in minimal_urls:
            response = create_short_url(test_db_session, url)
            assert response.short_code is not None


class TestEdgeCasesAPI:
    def test_post_shorten_empty_string_url(self, client):
        response = client.post("/shorten", json={"url": ""})
        assert response.status_code == 200

    def test_post_shorten_whitespace_url(self, client):
        response = client.post("/shorten", json={"url": "   "})
        assert response.status_code == 200

    def test_get_non_existent_short_code(self, client):
        response = client.get("/nonexistent123")
        assert response.status_code == 404

    def test_get_empty_short_code(self, client):
        response = client.get("/")
        assert response.status_code == 200

    def test_get_short_code_with_special_characters(self, client):
        special_codes = [
            "!@#$%^",
            "()_+{}[]",
            "a b c d",
            "../../../../etc/passwd",
        ]
        for code in special_codes:
            response = client.get(f"/{code}")
            assert response.status_code == 404

    def test_post_shorten_large_payload(self, client):
        large_url = "https://" + "x" * 5000 + ".com"
        response = client.post("/shorten", json={"url": large_url})
        assert response.status_code == 200
        data = response.json()
        assert data["short_code"] is not None
        assert data["original_url"] == large_url

    def test_post_shorten_unicode_urls(self, client):
        unicode_urls = [
            "https://例子.com/路径",
            "https://пример.рф/путь",
            "https://日本語.jp/パス",
        ]
        for url in unicode_urls:
            response = client.post("/shorten", json={"url": url})
            assert response.status_code == 200

    def test_post_shorten_same_url_multiple_times(self, client):
        url = "https://duplicate-multiple.com"
        codes = []
        for _ in range(5):
            response = client.post("/shorten", json={"url": url})
            data = response.json()
            codes.append(data["short_code"])
        assert len(set(codes)) == 1


class TestEdgeCasesDatabase:
    def test_concurrent_same_url_creation(self, test_db_session):
        url = "https://concurrent-same.com"
        response1 = create_short_url(test_db_session, url)
        response2 = create_short_url(test_db_session, url)
        assert response1.short_code == response2.short_code

    def test_stats_with_max_records(self, test_db_session):
        from backend.app.models.url import URLMapping
        from backend.app.services.url_service import get_short_code_stats
        from backend.app.config.settings import MAX_SHORT_CODE_ATTEMPTS

        for i in range(20):
            mapping = URLMapping(
                short_code=f"CODE{i:06d}",
                original_url=f"https://test{i}.com"
            )
            test_db_session.add(mapping)
        test_db_session.commit()

        stats = get_short_code_stats(test_db_session)
        assert stats["used_count"] == 20
        assert stats["oldest_accessed"] is not None
        assert stats["newest_accessed"] is not None


class TestEdgeCasesRedirect:
    def test_redirect_preserves_url_encoding(self, client, test_db_session):
        from backend.app.models.url import URLMapping
        encoded_url = "https://example.com/path%20with%20spaces?query=value%26more"
        mapping = URLMapping(short_code="ENC001", original_url=encoded_url)
        test_db_session.add(mapping)
        test_db_session.commit()

        response = client.get("/ENC001", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == encoded_url

    def test_redirect_with_complex_query_params(self, client, test_db_session):
        from backend.app.models.url import URLMapping
        complex_url = "https://example.com/search?q=test&sort=desc&page=1&filter=a%26b&utm_source=test"
        mapping = URLMapping(short_code="CMPLX1", original_url=complex_url)
        test_db_session.add(mapping)
        test_db_session.commit()

        response = client.get("/CMPLX1", follow_redirects=False)
        assert response.status_code == 302
        assert response.headers["location"] == complex_url


class TestEdgeCasesValidation:
    def test_post_shorten_invalid_json(self, client):
        response = client.post("/shorten", data="not valid json")
        assert response.status_code == 422

    def test_post_shorten_wrong_content_type(self, client):
        response = client.post(
            "/shorten",
            data='{"url": "https://test.com"}',
            headers={"Content-Type": "text/plain"}
        )
        assert response.status_code in [415, 422]

    def test_get_short_code_case_sensitivity(self, client, test_db_session):
        from backend.app.models.url import URLMapping
        mapping_lower = URLMapping(short_code="abc123", original_url="https://lower.com")
        mapping_upper = URLMapping(short_code="ABC123", original_url="https://upper.com")
        test_db_session.add_all([mapping_lower, mapping_upper])
        test_db_session.commit()

        response_lower = client.get("/abc123", follow_redirects=False)
        response_upper = client.get("/ABC123", follow_redirects=False)

        assert response_lower.headers["location"] == "https://lower.com"
        assert response_upper.headers["location"] == "https://upper.com"
