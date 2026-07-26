"""
Unit tests for the URL shortener.

Run with: pytest tests/
"""

import pytest
from app.shortener import encode, decode, URLShortener
from app.storage import InMemoryStorage


class TestBase62Encoding:
    def test_zero_encodes_to_first_character(self):
        assert encode(0) == "0"

    def test_encode_decode_round_trip(self):
        for number in [0, 1, 61, 62, 1000, 999999]:
            assert decode(encode(number)) == number

    def test_encoding_is_deterministic(self):
        assert encode(12345) == encode(12345)

    def test_larger_numbers_produce_longer_codes(self):
        assert len(encode(1)) <= len(encode(10 ** 10))


class TestURLShortener:
    def setup_method(self):
        self.storage = InMemoryStorage()
        self.shortener = URLShortener(self.storage, min_code_length=4)

    def test_shorten_returns_a_code(self):
        code = self.shortener.shorten("https://example.com/some/long/path")
        assert isinstance(code, str)
        assert len(code) >= 4

    def test_shorten_then_resolve_returns_original_url(self):
        url = "https://example.com/article/12345"
        code = self.shortener.shorten(url)
        assert self.shortener.resolve(code) == url

    def test_resolve_unknown_code_returns_none(self):
        assert self.shortener.resolve("zzzz") is None

    def test_rejects_url_without_scheme(self):
        with pytest.raises(ValueError):
            self.shortener.shorten("example.com/no-scheme")

    def test_different_urls_get_different_codes(self):
        code_a = self.shortener.shorten("https://example.com/a")
        code_b = self.shortener.shorten("https://example.com/b")
        assert code_a != code_b

    def test_shortener_works_across_storage_backends(self):
        # Same test logic, different storage implementation, proving
        # the service layer genuinely doesn't care which backend it
        # talks to.
        from app.storage import SQLiteStorage
        import tempfile
        import os

        with tempfile.TemporaryDirectory() as tmp_dir:
            db_path = os.path.join(tmp_dir, "test.db")
            sqlite_storage = SQLiteStorage(db_path)
            sqlite_shortener = URLShortener(sqlite_storage)

            url = "https://example.com/sqlite-test"
            code = sqlite_shortener.shorten(url)
            assert sqlite_shortener.resolve(code) == url
