from datetime import datetime, timedelta
from unittest.mock import patch
from sqlalchemy import func

from backend.app.models.url import URLMapping
from backend.app.services.url_service import (
    get_short_code_stats,
    get_url_mapping,
    update_access_time,
    create_short_url,
)
from backend.app.config.settings import MAX_SHORT_CODE_ATTEMPTS


class TestGetURLMapping:
    def test_get_url_mapping_exists(self, test_db_session, sample_url_mappings):
        mapping = get_url_mapping(test_db_session, "abc123")
        assert mapping is not None
        assert mapping.short_code == "abc123"
        assert mapping.original_url == "https://example.com"

    def test_get_url_mapping_not_exists(self, test_db_session):
        mapping = get_url_mapping(test_db_session, "nonexistent")
        assert mapping is None


class TestUpdateAccessTime:
    def test_update_access_time_updates_timestamp(self, test_db_session, sample_url_mappings):
        mapping = sample_url_mappings[0]
        original_time = mapping.last_accessed_at
        update_access_time(test_db_session, mapping)
        test_db_session.refresh(mapping)
        assert mapping.last_accessed_at > original_time

    def test_update_access_time_persists_to_db(self, test_db_session, sample_url_mappings):
        mapping = sample_url_mappings[0]
        original_time = mapping.last_accessed_at
        update_access_time(test_db_session, mapping)
        refreshed = test_db_session.query(URLMapping).filter_by(short_code="abc123").first()
        assert refreshed.last_accessed_at > original_time


class TestGetShortCodeStats:
    def test_stats_with_empty_database(self, test_db_session):
        stats = get_short_code_stats(test_db_session)
        assert stats["used_count"] == 0
        assert stats["usage_percent"] == 0.0
        assert stats["oldest_accessed"] is None
        assert stats["newest_accessed"] is None

    def test_stats_with_data(self, test_db_session, sample_url_mappings):
        stats = get_short_code_stats(test_db_session)
        assert stats["used_count"] == 3
        assert stats["available_count"] > 0
        assert 0 <= stats["usage_percent"] < 100
        assert stats["oldest_accessed"] is not None
        assert stats["newest_accessed"] is not None

    def test_stats_available_count_calculation(self, test_db_session, sample_url_mappings):
        from backend.app.utils.short_code import TOTAL_SHORT_CODE_POOL
        stats = get_short_code_stats(test_db_session)
        assert stats["used_count"] + stats["available_count"] == TOTAL_SHORT_CODE_POOL


class TestCreateShortURL:
    def test_create_new_short_url(self, test_db_session):
        url = "https://newexample.com"
        response = create_short_url(test_db_session, url)
        assert response.short_code is not None
        assert response.original_url == url
        assert response.is_reused is False
        assert response.replaced_url is None

        mapping = get_url_mapping(test_db_session, response.short_code)
        assert mapping is not None
        assert mapping.original_url == url

    def test_create_duplicate_url_reuses_short_code(self, test_db_session, sample_url_mappings):
        existing = sample_url_mappings[0]
        original_time = existing.last_accessed_at
        response = create_short_url(test_db_session, "https://example.com")
        test_db_session.refresh(existing)
        assert response.short_code == existing.short_code
        assert response.is_reused is False
        assert existing.last_accessed_at > original_time

    def test_create_short_url_generates_unique_code(self, test_db_session):
        urls = ["https://a.com", "https://b.com", "https://c.com"]
        codes = []
        for url in urls:
            resp = create_short_url(test_db_session, url)
            codes.append(resp.short_code)
        assert len(set(codes)) == len(urls)

    def test_short_code_length_and_format(self, test_db_session):
        response = create_short_url(test_db_session, "https://test.com")
        assert len(response.short_code) == 6
        assert response.short_code.isalnum()


class TestLRUReplacement:
    def test_lru_replacement_when_pool_full(self, test_db_session, monkeypatch):
        from backend.app.services import url_service as url_service_module
        
        original_generate = url_service_module.generate_short_code
        mock_code = "MOCK12"
        
        existing_codes = []
        for i in range(MAX_SHORT_CODE_ATTEMPTS + 1):
            mapping = URLMapping(
                short_code=f"CODE{i:04d}",
                original_url=f"https://test{i}.com"
            )
            if i == 0:
                mapping.last_accessed_at = datetime.utcnow() - timedelta(days=100)
            elif i == MAX_SHORT_CODE_ATTEMPTS:
                mapping.last_accessed_at = datetime.utcnow() - timedelta(days=1)
            else:
                mapping.last_accessed_at = datetime.utcnow() - timedelta(days=50)
            test_db_session.add(mapping)
            existing_codes.append(f"CODE{i:04d}")
        test_db_session.commit()
        
        def mock_generate():
            return existing_codes[0]
        
        monkeypatch.setattr(url_service_module, 'generate_short_code', mock_generate)
        
        new_url = "https://new-domain.com"
        response = create_short_url(test_db_session, new_url)
        
        assert response.is_reused is True
        assert response.replaced_url is not None
        assert "https://test0.com" in response.replaced_url
        assert response.original_url == new_url
        
        updated = test_db_session.query(URLMapping).filter_by(
            short_code=existing_codes[0]
        ).first()
        assert updated.original_url == new_url

    def test_lru_chooses_oldest_accessed(self, test_db_session, monkeypatch):
        from backend.app.services import url_service as url_service_module
        
        base_time = datetime.utcnow()
        urls_times = [
            ("oldest", base_time - timedelta(days=10)),
            ("middle", base_time - timedelta(days=5)),
            ("newest", base_time - timedelta(hours=1)),
        ]
        
        for name, access_time in urls_times:
            mapping = URLMapping(
                short_code=name.upper(),
                original_url=f"https://{name}.com"
            )
            mapping.last_accessed_at = access_time
            test_db_session.add(mapping)
        test_db_session.commit()
        
        def mock_generate():
            return "OLDEST"
        
        monkeypatch.setattr(url_service_module, 'generate_short_code', mock_generate)
        
        new_url = "https://replaced.com"
        response = create_short_url(test_db_session, new_url)
        
        assert response.is_reused is True
        assert response.short_code == "OLDEST"
        assert response.replaced_url == "https://oldest.com"
