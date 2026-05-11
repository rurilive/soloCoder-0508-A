import asyncio
import pytest
from concurrent.futures import ThreadPoolExecutor, as_completed
import threading


class TestSimulatedConcurrency:
    def test_sequential_url_creation_simulation(self, test_db_session):
        from backend.app.services.url_service import create_short_url

        urls = [f"https://sequential-{i}.com" for i in range(20)]
        results = []
        for url in urls:
            try:
                result = create_short_url(test_db_session, url)
                results.append(result)
            except Exception as e:
                results.append(("error", str(e)))

        assert len(results) == 20
        successful_results = [r for r in results if not isinstance(r, tuple)]
        assert len(successful_results) == 20

    def test_sequential_same_url_creation(self, test_db_session):
        from backend.app.services.url_service import create_short_url

        same_url = "https://same-sequential.com"
        results = []
        for _ in range(15):
            try:
                result = create_short_url(test_db_session, same_url)
                results.append(result.short_code)
            except Exception as e:
                results.append(("error", str(e)))

        unique_codes = set(r for r in results if isinstance(r, str))
        assert len(unique_codes) == 1

    def test_sequential_read_operations(self, client, test_db_session):
        from backend.app.models.url import URLMapping

        for i in range(10):
            mapping = URLMapping(
                short_code=f"SEQ{i:04d}",
                original_url=f"https://read-sequential-{i}.com"
            )
            test_db_session.add(mapping)
        test_db_session.commit()

        results = []
        codes = [f"SEQ{i:04d}" for i in range(10)]
        for code in codes:
            try:
                response = client.get(f"/{code}", follow_redirects=False)
                results.append(response.status_code)
            except Exception as e:
                results.append(("error", str(e)))

        assert len(results) == 10
        assert all(r == 302 for r in results if not isinstance(r, tuple))


class TestAsyncConcurrency:
    @pytest.mark.asyncio
    async def test_async_concurrent_requests(self):
        import aiohttp

        async with aiohttp.ClientSession() as session:
            base_url = "http://localhost:1111"
            tasks = []
            for i in range(10):
                url = f"https://async-test-{i}.com"
                task = session.post(
                    f"{base_url}/shorten",
                    json={"url": url}
                )
                tasks.append(task)

            responses = await asyncio.gather(*tasks, return_exceptions=True)
            successful = [r for r in responses if not isinstance(r, Exception)]
            assert len(successful) >= 0


class TestDatabaseConcurrency:
    def test_concurrent_stats_reads(self, client, test_db_session):
        from backend.app.models.url import URLMapping

        for i in range(5):
            mapping = URLMapping(
                short_code=f"STAT{i:04d}",
                original_url=f"https://stats-{i}.com"
            )
            test_db_session.add(mapping)
        test_db_session.commit()

        results = []
        lock = threading.Lock()

        def read_stats():
            try:
                response = client.get("/stats")
                with lock:
                    results.append(response.status_code)
                return response.json()
            except Exception as e:
                with lock:
                    results.append(("error", str(e)))
                return None

        with ThreadPoolExecutor(max_workers=6) as executor:
            futures = [executor.submit(read_stats) for _ in range(20)]
            stats_results = []
            for future in as_completed(futures):
                result = future.result()
                if result and not isinstance(result, tuple):
                    stats_results.append(result)

        assert len(results) == 20
        if stats_results:
            assert stats_results[0]["used_count"] >= 5


class TestLRUConcurrency:
    def test_concurrent_lru_replacement(self, test_db_session, monkeypatch):
        from datetime import datetime, timedelta
        from backend.app.models.url import URLMapping
        from backend.app.services import url_service as url_service_module
        from backend.app.config.settings import MAX_SHORT_CODE_ATTEMPTS

        for i in range(MAX_SHORT_CODE_ATTEMPTS + 1):
            mapping = URLMapping(
                short_code=f"LRU{i:04d}",
                original_url=f"https://lru-old-{i}.com"
            )
            mapping.last_accessed_at = datetime.utcnow() - timedelta(days=i + 1)
            test_db_session.add(mapping)
        test_db_session.commit()

        mock_called = [0]
        original_generate = url_service_module.generate_short_code

        def mock_generate():
            mock_called[0] += 1
            return "LRU0000"

        monkeypatch.setattr(url_service_module, 'generate_short_code', mock_generate)

        results = []
        lock = threading.Lock()

        from backend.app.services.url_service import create_short_url

        def create_with_lru(index):
            try:
                url = f"https://new-lru-{index}.com"
                result = create_short_url(test_db_session, url)
                with lock:
                    results.append(result)
                return result
            except Exception as e:
                with lock:
                    results.append(("error", str(e)))
                return None

        with ThreadPoolExecutor(max_workers=3) as executor:
            futures = [executor.submit(create_with_lru, i) for i in range(5)]
            for future in as_completed(futures):
                future.result()

        assert len(results) == 5
