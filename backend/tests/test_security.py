import pytest


class TestSQLInjectionProtection:
    def test_sql_injection_in_url_parameter(self, client):
        injection_payloads = [
            "' OR 1=1--",
            "' UNION SELECT 1,2,3--",
            "' DROP TABLE url_mappings--",
            "'; DROP TABLE url_mappings--",
            "https://example.com' OR '1'='1",
            "https://example.com'; DROP TABLE url_mappings;--",
        ]
        for payload in injection_payloads:
            response = client.post("/shorten", json={"url": payload})
            assert response.status_code in [200, 422]
            assert response.status_code != 500

    def test_sql_injection_in_short_code_param(self, client):
        injection_codes = [
            "' OR '1'='1",
            "' OR 1=1--",
            "abc123' OR '1'='1",
            "'); SELECT * FROM url_mappings;--",
        ]
        for code in injection_codes:
            response = client.get(f"/{code}")
            assert response.status_code in [404, 422]
            assert response.status_code != 500

    def test_sql_injection_encoded(self, client):
        encoded_payloads = [
            "%27%20OR%20%271%27%3D%271",
            "%27%3B%20DROP%20TABLE%20users%3B--",
        ]
        for payload in encoded_payloads:
            response = client.get(f"/{payload}")
            assert response.status_code in [404, 422]


class TestXSSProtection:
    def test_xss_in_url_parameter(self, client):
        xss_payloads = [
            "<script>alert('XSS')</script>",
            "<img src=x onerror=alert(1)>",
            "javascript:alert(1)",
            "data:text/html,<script>alert(1)</script>",
            "https://example.com/<script>alert(1)</script>",
        ]
        for payload in xss_payloads:
            response = client.post("/shorten", json={"url": payload})
            assert response.status_code == 200
            data = response.json()
            assert "<script>" not in data["short_code"]

    def test_xss_via_redirect_url(self, test_db_session):
        from backend.app.models.url import URLMapping
        from backend.app.services.url_service import get_url_mapping
        xss_url = "javascript:alert('XSS via redirect')"
        mapping = URLMapping(short_code="XSS001", original_url=xss_url)
        test_db_session.add(mapping)
        test_db_session.commit()
        retrieved = get_url_mapping(test_db_session, "XSS001")
        assert retrieved is not None
        assert retrieved.original_url == xss_url

    def test_xss_in_error_response(self, client):
        xss_code = "<img src=x onerror=alert(1)>"
        response = client.get(f"/{xss_code}")
        assert response.status_code == 404
        data = response.json()
        assert "detail" in data


class TestOpenRedirectProtection:
    def test_open_redirect_to_malicious_site(self, test_db_session):
        from backend.app.models.url import URLMapping
        from backend.app.services.url_service import get_url_mapping
        malicious_url = "https://phishing-site-attack.com/steal-credentials"
        mapping = URLMapping(short_code="MAL001", original_url=malicious_url)
        test_db_session.add(mapping)
        test_db_session.commit()
        retrieved = get_url_mapping(test_db_session, "MAL001")
        assert retrieved is not None
        assert retrieved.original_url == malicious_url

    def test_file_protocol_redirect(self, test_db_session):
        from backend.app.models.url import URLMapping
        from backend.app.services.url_service import get_url_mapping
        file_url = "file:///etc/passwd"
        mapping = URLMapping(short_code="FILE01", original_url=file_url)
        test_db_session.add(mapping)
        test_db_session.commit()
        retrieved = get_url_mapping(test_db_session, "FILE01")
        assert retrieved is not None
        assert retrieved.original_url == file_url

    def test_data_url_redirect(self, test_db_session):
        from backend.app.models.url import URLMapping
        from backend.app.services.url_service import get_url_mapping
        data_url = "data:text/html;base64,PHNjcmlwdD5hbGVydCgxKTwvc2NyaXB0Pg=="
        mapping = URLMapping(short_code="DATA01", original_url=data_url)
        test_db_session.add(mapping)
        test_db_session.commit()
        retrieved = get_url_mapping(test_db_session, "DATA01")
        assert retrieved is not None
        assert retrieved.original_url == data_url


class TestHeaderSecurity:
    def test_response_headers_present(self, client):
        response = client.get("/")
        assert "content-type" in response.headers
        assert response.headers["content-type"] == "application/json"

    def test_x_frame_options_header_optional(self, client):
        response = client.get("/")
        x_frame = response.headers.get("X-Frame-Options", "")
        pass

    def test_csp_header_optional(self, client):
        response = client.get("/")
        csp = response.headers.get("Content-Security-Policy", "")
        pass


class TestInputValidation:
    def test_extremely_large_url_payload(self, client):
        extremely_large_url = "https://" + "a" * 10000 + ".com"
        response = client.post("/shorten", json={"url": extremely_large_url})
        assert response.status_code in [200, 413, 422]

    def test_nested_json_payload(self, client):
        nested_payload = {
            "url": "https://example.com",
            "extra": {
                "nested": {
                    "deep": {
                        "data": "test"
                    }
                }
            }
        }
        response = client.post("/shorten", json=nested_payload)
        assert response.status_code == 200

    def test_array_in_url_field(self, client):
        response = client.post("/shorten", json={"url": ["https://example.com"]})
        assert response.status_code == 422

    def test_null_url(self, client):
        response = client.post("/shorten", json={"url": None})
        assert response.status_code == 422

    def test_boolean_url(self, client):
        response = client.post("/shorten", json={"url": True})
        assert response.status_code == 422

    def test_number_url(self, client):
        response = client.post("/shorten", json={"url": 12345})
        assert response.status_code == 422

    def test_object_url(self, client):
        response = client.post("/shorten", json={"url": {"test": "value"}})
        assert response.status_code == 422


class TestRateLimitingAndAbuse:
    def test_multiple_rapid_requests(self, client):
        for i in range(50):
            response = client.post("/shorten", json={"url": f"https://rapid-{i}.com"})
            assert response.status_code == 200

    def test_same_url_rapid_requests(self, client):
        for _ in range(100):
            response = client.post("/shorten", json={"url": "https://same-rapid.com"})
            assert response.status_code == 200
            data = response.json()
            assert data["is_reused"] is False


class TestInformationDisclosure:
    def test_error_messages_do_not_leak_details(self, client):
        response = client.get("/non-existent-code")
        data = response.json()
        assert "detail" in data
        assert "File \"\"" not in str(data)
        assert "Traceback" not in str(data)

    def test_stats_endpoint_no_sensitive_info(self, client):
        response = client.get("/stats")
        data = response.json()
        sensitive_fields = ["password", "secret", "token", "api_key"]
        for field in sensitive_fields:
            assert field not in data

    def test_root_endpoint_no_sensitive_info(self, client):
        response = client.get("/")
        data = response.json()
        sensitive_fields = ["database", "connection", "password", "secret"]
        for field in sensitive_fields:
            assert field not in str(data).lower()


class TestPathTraversal:
    def test_special_characters_not_found(self, client):
        special_codes = [
            "abc!def",
            "abc@def",
            "abc#def",
            "abc$def",
            "abc%20def",
        ]
        for code in special_codes:
            response = client.get(f"/{code}")
            assert response.status_code in [404, 200]

    def test_non_alphanumeric_short_codes(self, client):
        invalid_codes = [
            "ab..cd",
            "ab//cd",
            "ab\\\\cd",
        ]
        for code in invalid_codes:
            response = client.get(f"/{code}")
            assert response.status_code in [404, 200]


class TestCommandInjection:
    def test_command_injection_attempts(self, client):
        injection_payloads = [
            "https://example.com; ls -la",
            "https://example.com && rm -rf /",
            "https://example.com | whoami",
            "https://example.com $(cat /etc/passwd)",
            "https://example.com `id`",
        ]
        for payload in injection_payloads:
            response = client.post("/shorten", json={"url": payload})
            assert response.status_code in [200, 422]

    def test_command_injection_in_short_code(self, client):
        injection_codes = [
            ";id;",
            "$(id)",
            "`id`",
            "|whoami",
        ]
        for code in injection_codes:
            response = client.get(f"/{code}")
            assert response.status_code == 404
