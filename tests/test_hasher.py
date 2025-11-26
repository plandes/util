import unittest
from zensols.util import APIError
from zensols.util.hasher import Hasher


class TestHasher(unittest.TestCase):
    def test_default_url_hash_short(self):
        # default (short=20, decode='url') should be deterministic and URL-safe
        h1 = Hasher()  # default: short=20, decode='url'
        h1.update(b"hello world")
        t1 = h1()

        h2 = Hasher()
        h2.update(b"hello world")
        t2 = h2()

        # same input → same output
        self.assertEqual(t1, t2)

        # URL-safe base64 chars only
        self.assertRegex(t1, r"^[A-Za-z0-9_-]+$")

        # should be reasonably short (20-byte digest -> ~27 chars)
        self.assertLessEqual(len(t1), 30)
        self.assertGreaterEqual(len(t1), 20)

    def test_default_url_diff_inputs_diff_tokens(self):
        h1 = Hasher()
        h1.update(b"content A")
        t1 = h1()

        h2 = Hasher()
        h2.update(b"content B")
        t2 = h2()

        self.assertNotEqual(t1, t2)

    def test_hex_encoding_length_matches_digest_size(self):
        # for hex, length should be 2 * digest_size
        h = Hasher(short=20, decode="hex")  # 20-byte digest
        h.update(b"some data")
        token = h()

        self.assertRegex(token, r"^[0-9a-f]+$")
        self.assertEqual(len(token), 40)  # 2 * 20

    def test_blake2b_selected_for_large_digest(self):
        # short > 32 should pick blake2b and allow larger digests
        h = Hasher(short=40, decode="hex")  # should switch to blake2b
        h.update(b"some data")
        token = h()

        # 40-byte digest → 80 hex chars
        self.assertEqual(len(token), 80)

    def test_invalid_digest_size_zero_raises(self):
        with self.assertRaises(APIError):
            Hasher(short=0)

    def test_invalid_digest_size_too_large_raises(self):
        # >64 bytes should fail __post_init__ logic
        with self.assertRaises(APIError):
            Hasher(short=65)
