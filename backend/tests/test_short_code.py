import string
import pytest

from backend.app.utils.short_code import generate_short_code, TOTAL_SHORT_CODE_POOL
from backend.app.config.settings import SHORT_CODE_LENGTH, CHARACTERS


def test_total_short_code_pool():
    assert TOTAL_SHORT_CODE_POOL == len(CHARACTERS) ** SHORT_CODE_LENGTH
    assert TOTAL_SHORT_CODE_POOL == 62 ** 6
    assert TOTAL_SHORT_CODE_POOL == 56800235584


def test_generate_short_code_length():
    code = generate_short_code()
    assert len(code) == SHORT_CODE_LENGTH


def test_generate_short_code_charset():
    code = generate_short_code()
    for char in code:
        assert char in CHARACTERS
        assert char in (string.ascii_letters + string.digits)


def test_generate_short_code_uniqueness():
    codes = [generate_short_code() for _ in range(100)]
    assert len(set(codes)) > 1
    for code in codes:
        assert len(code) == SHORT_CODE_LENGTH
        assert all(c in CHARACTERS for c in code)


@pytest.mark.parametrize("iterations", [10, 50, 100])
def test_generate_short_code_consistency(iterations):
    for _ in range(iterations):
        code = generate_short_code()
        assert isinstance(code, str)
        assert len(code) == SHORT_CODE_LENGTH
        assert code.isalnum()
