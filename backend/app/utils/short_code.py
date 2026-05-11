import random

from ..config.settings import SHORT_CODE_LENGTH, CHARACTERS


TOTAL_SHORT_CODE_POOL = len(CHARACTERS) ** SHORT_CODE_LENGTH


def generate_short_code() -> str:
    return "".join(random.choices(CHARACTERS, k=SHORT_CODE_LENGTH))
