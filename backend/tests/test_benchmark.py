import pytest
from backend.app.utils.short_code import generate_short_code
from backend.app.services.url_service import (
    create_short_url,
    get_short_code_stats,
    get_url_mapping,
    update_access_time,
)


class TestBenchmarkShortCodeGeneration:
    def test_generate_short_code_benchmark(self, benchmark):
        result = benchmark(generate_short_code)
        assert len(result) == 6
        assert result.isalnum()

    def test_generate_100_short_codes_benchmark(self, benchmark):
        def generate_many():
            return [generate_short_code() for _ in range(100)]
        results = benchmark(generate_many)
        assert len(results) == 100
        assert len(set(results)) > 50


class TestBenchmarkURLCreation:
    def test_create_short_url_benchmark(self, benchmark, test_db_session):
        url = "https://benchmark-test.com"
        result = benchmark(create_short_url, test_db_session, url)
        assert result.short_code is not None
        assert result.original_url == url

    def test_create_multiple_short_urls_benchmark(self, benchmark, test_db_session):
        def create_many():
            results = []
            for i in range(10):
                url = f"https://benchmark-{i}.com"
                result = create_short_url(test_db_session, url)
                results.append(result)
            return results
        results = benchmark(create_many)
        assert len(results) == 10


class TestBenchmarkURLRetrieval:
    def test_get_url_mapping_benchmark(self, benchmark, test_db_session):
        from backend.app.models.url import URLMapping
        mapping = URLMapping(short_code="BENCH1", original_url="https://benchmark-retrieve.com")
        test_db_session.add(mapping)
        test_db_session.commit()
        result = benchmark(get_url_mapping, test_db_session, "BENCH1")
        assert result is not None
        assert result.short_code == "BENCH1"

    def test_get_short_code_stats_benchmark(self, benchmark, test_db_session):
        result = benchmark(get_short_code_stats, test_db_session)
        assert "used_count" in result
        assert "total_pool" in result


class TestBenchmarkUpdateAccessTime:
    def test_update_access_time_benchmark(self, benchmark, test_db_session):
        from backend.app.models.url import URLMapping
        mapping = URLMapping(short_code="UPDATE1", original_url="https://benchmark-update.com")
        test_db_session.add(mapping)
        test_db_session.commit()
        benchmark(update_access_time, test_db_session, mapping)
        test_db_session.refresh(mapping)
        assert mapping.last_accessed_at is not None


class TestBenchmarkAPIRoutes:
    def test_root_endpoint_benchmark(self, benchmark, client):
        result = benchmark(client.get, "/")
        assert result.status_code == 200

    def test_stats_endpoint_benchmark(self, benchmark, client):
        result = benchmark(client.get, "/stats")
        assert result.status_code == 200

    def test_shorten_endpoint_benchmark(self, benchmark, client):
        url = "https://api-benchmark.com"
        result = benchmark(client.post, "/shorten", json={"url": url})
        assert result.status_code == 200
        data = result.json()
        assert "short_code" in data

    def test_redirect_endpoint_benchmark(self, benchmark, client, test_db_session):
        from backend.app.models.url import URLMapping
        mapping = URLMapping(short_code="APIBEN", original_url="https://redirect-benchmark.com")
        test_db_session.add(mapping)
        test_db_session.commit()
        result = benchmark(client.get, "/APIBEN", follow_redirects=False)
        assert result.status_code == 302


class TestBenchmarkWithData:
    def test_create_100_urls_benchmark(self, benchmark, test_db_session):
        def create_100_urls():
            results = []
            for i in range(100):
                url = f"https://bulk-{i}.com"
                result = create_short_url(test_db_session, url)
                results.append(result)
            return results
        results = benchmark(create_100_urls)
        assert len(results) == 100

    def test_stats_with_many_records_benchmark(self, benchmark, test_db_session):
        from backend.app.models.url import URLMapping
        for i in range(50):
            mapping = URLMapping(
                short_code=f"STATS{i:04d}",
                original_url=f"https://stats-test-{i}.com"
            )
            test_db_session.add(mapping)
        test_db_session.commit()
        result = benchmark(get_short_code_stats, test_db_session)
        assert result["used_count"] >= 50


class TestBenchmarkLRU:
    def test_lru_replacement_benchmark(self, benchmark, test_db_session, monkeypatch):
        from datetime import datetime, timedelta
        from backend.app.services.url_service import create_short_url
        from backend.app.services import url_service as url_service_module
        from backend.app.config.settings import MAX_SHORT_CODE_ATTEMPTS

        def setup():
            from backend.app.models.url import URLMapping
            for i in range(MAX_SHORT_CODE_ATTEMPTS + 1):
                mapping = URLMapping(
                    short_code=f"LRUB{i:04d}",
                    original_url=f"https://lru-bench-{i}.com"
                )
                mapping.last_accessed_at = datetime.utcnow() - timedelta(days=i + 1)
                test_db_session.add(mapping)
            test_db_session.commit()

            def mock_generate():
                return "LRUB0000"

            monkeypatch.setattr(url_service_module, 'generate_short_code', mock_generate)

        def perform_lru():
            url = "https://new-lru-bench.com"
            return create_short_url(test_db_session, url)

        result = benchmark.pedantic(
            perform_lru, setup=setup, iterations=1, rounds=1
        )
        assert result is not None
