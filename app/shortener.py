"""
Core URL shortening logic.

Uses base62 encoding of an incrementing counter to generate short
codes. Base62 (0-9, a-z, A-Z) is the standard choice for this problem
because every character in the output is URL-safe with no need for
escaping, unlike base64.

Collision handling: since codes are derived from a monotonically
increasing counter rather than a hash, collisions are only possible if
the same code is requested twice, which the storage layer's exists()
check guards against.
"""

import string
from app.storage import URLStorage

ALPHABET = string.digits + string.ascii_lowercase + string.ascii_uppercase
BASE = len(ALPHABET)  # 62


def encode(number: int) -> str:
    """
    Convert a non-negative integer to a base62 string.

    Time complexity: O(log62 n), since each division peels off one
    base62 digit. For any realistic counter size this is effectively
    constant time (a 64-bit counter needs at most 11 characters).
    """
    if number == 0:
        return ALPHABET[0]

    digits = []
    while number > 0:
        number, remainder = divmod(number, BASE)
        digits.append(ALPHABET[remainder])

    return "".join(reversed(digits))


def decode(code: str) -> int:
    """Convert a base62 string back to its integer value."""
    number = 0
    for char in code:
        number = number * BASE + ALPHABET.index(char)
    return number


class URLShortener:
    """
    Service layer that ties the encoding algorithm to a storage
    backend. The storage parameter is typed as the abstract URLStorage
    interface, not a concrete class, so any backend that implements
    that interface works here without modification.
    """

    def __init__(self, storage: URLStorage, min_code_length: int = 4):
        self._storage = storage
        self._min_code_length = min_code_length
        self._counter = storage.count()

    def shorten(self, long_url: str) -> str:
        """
        Generate a short code for a URL and persist the mapping.
        Returns the short code (not the full short URL, that's a
        presentation-layer concern handled by the API route).
        """
        if not long_url or not long_url.startswith(("http://", "https://")):
            raise ValueError("long_url must be a valid absolute URL")

        self._counter += 1
        code = encode(self._counter).rjust(self._min_code_length, ALPHABET[0])

        # Defensive check, see collision note in module docstring.
        while self._storage.exists(code):
            self._counter += 1
            code = encode(self._counter).rjust(self._min_code_length, ALPHABET[0])

        self._storage.save(code, long_url)
        return code

    def resolve(self, short_code: str) -> str | None:
        """Look up the original URL for a short code. O(1) average
        case since both storage backends use a hash-based lookup."""
        return self._storage.get(short_code)
