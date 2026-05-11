import pytest
import subprocess
import time
import httpx


@pytest.fixture(scope="module")
def backend_server():
    process = subprocess.Popen(
        ["uv", "run", "python", "main.py"],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    time.sleep(2)
    try:
        yield process
    finally:
        process.terminate()
        process.wait(timeout=10)


@pytest.mark.skip(reason="Requires running server")
class TestE2EBackendAPI:
    async def test_full_url_shortening_flow(self, backend_server):
        async with httpx.AsyncClient(base_url="http://localhost:1111") as client:
            original_url = "https://e2e-test-full-flow.com"
            response = await client.post("/shorten", json={"url": original_url})
            assert response.status_code == 200
            data = response.json()
            short_code = data["short_code"]
            assert data["original_url"] == original_url
            assert len(short_code) == 6

            redirect_response = await client.get(f"/{short_code}", follow_redirects=False)
            assert redirect_response.status_code == 302
            assert redirect_response.headers["location"] == original_url

    async def test_e2e_stats_endpoint(self, backend_server):
        async with httpx.AsyncClient(base_url="http://localhost:1111") as client:
            response = await client.get("/stats")
            assert response.status_code == 200
            data = response.json()
            assert "total_pool" in data
            assert "used_count" in data
            assert "available_count" in data

    async def test_e2e_multiple_creations(self, backend_server):
        async with httpx.AsyncClient(base_url="http://localhost:1111") as client:
            urls = [
                "https://e2e-1.com",
                "https://e2e-2.com",
                "https://e2e-3.com",
                "https://e2e-4.com",
                "https://e2e-5.com",
            ]
            codes = []
            for url in urls:
                response = await client.post("/shorten", json={"url": url})
                assert response.status_code == 200
                codes.append(response.json()["short_code"])

            stats = await client.get("/stats")
            stats_data = stats.json()
            assert stats_data["used_count"] >= 5

            for code, url in zip(codes, urls):
                redirect = await client.get(f"/{code}", follow_redirects=False)
                assert redirect.status_code == 302
                assert redirect.headers["location"] == url

    async def test_e2e_duplicate_url(self, backend_server):
        async with httpx.AsyncClient(base_url="http://localhost:1111") as client:
            url = "https://e2e-duplicate.com"
            response1 = await client.post("/shorten", json={"url": url})
            code1 = response1.json()["short_code"]

            response2 = await client.post("/shorten", json={"url": url})
            code2 = response2.json()["short_code"]

            assert code1 == code2
            assert response2.json()["is_reused"] is False

    async def test_e2e_not_found(self, backend_server):
        async with httpx.AsyncClient(base_url="http://localhost:1111") as client:
            response = await client.get("/nonexistent-e2e-code")
            assert response.status_code == 404
            data = response.json()
            assert "detail" in data

    async def test_e2e_root_endpoint(self, backend_server):
        async with httpx.AsyncClient(base_url="http://localhost:1111") as client:
            response = await client.get("/")
            assert response.status_code == 200
            data = response.json()
            assert "service" in data
            assert "endpoints" in data


@pytest.mark.skip(reason="Requires Playwright browsers")
class TestE2EFrontend:
    async def test_frontend_home_page_loads(self, page):
        await page.goto("http://localhost:3000")
        assert "URL 缩短服务" in await page.title()

    async def test_frontend_shorten_url(self, page):
        await page.goto("http://localhost:3000")
        await page.fill('input[type="url"]', "https://playwright-test.com")
        await page.click('button[type="submit"]')
        await page.wait_for_selector('.result-card')
        assert "缩短成功！" in await page.content()

    async def test_frontend_stats_button(self, page):
        await page.goto("http://localhost:3000")
        await page.click('text=查看统计数据')
        await page.wait_for_selector('.stats-card')
        assert "短码池统计" in await page.content()

    async def test_frontend_copy_functionality(self, page):
        await page.goto("http://localhost:3000")
        await page.fill('input[type="url"]', "https://copy-test.com")
        await page.click('button[type="submit"]')
        await page.wait_for_selector('button:text("复制")')
        await page.click('button:text("复制")')

    async def test_frontend_error_display(self, page):
        page.route("**/api/shorten", lambda route: route.fulfill(
            status=400,
            json={"detail": "Test error"}
        ))
        await page.goto("http://localhost:3000")
        await page.fill('input[type="url"]', "https://error-test.com")
        await page.click('button[type="submit"]')
        await page.wait_for_selector('.error-message')
        assert "Test error" in await page.content()


class TestE2ELoadScenario:
    @pytest.mark.skip(reason="Integration test - run manually")
    async def test_high_load_scenario(self):
        import asyncio

        async def make_request(client, i):
            url = f"https://load-test-{i}.com"
            response = await client.post("/shorten", json={"url": url})
            return response.status_code

        async with httpx.AsyncClient(base_url="http://localhost:1111") as client:
            tasks = [make_request(client, i) for i in range(100)]
            responses = await asyncio.gather(*tasks)
            success_count = sum(1 for r in responses if r == 200)
            assert success_count > 90
