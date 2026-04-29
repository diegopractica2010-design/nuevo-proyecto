import unittest

from backend.infrastructure.cache.cache import cache_get, cache_set, set_cache_client


class FakeRedis:
    def __init__(self):
        self.values = {}
        self.ttls = {}

    def get(self, key):
        return self.values.get(key)

    def set(self, key, value, ex=None):
        self.values[key] = value
        self.ttls[key] = ex
        return True


class CacheTests(unittest.TestCase):
    def setUp(self):
        self.client = FakeRedis()
        set_cache_client(self.client)

    def tearDown(self):
        set_cache_client(None)

    def test_cache_set_and_get_json_value(self):
        saved = cache_set("search:arroz", {"count": 1, "items": ["arroz"]}, ttl=120)

        self.assertTrue(saved)
        self.assertEqual(cache_get("search:arroz"), {"count": 1, "items": ["arroz"]})
        self.assertEqual(self.client.ttls["search:arroz"], 120)

    def test_cache_get_missing_key_returns_none(self):
        self.assertIsNone(cache_get("missing"))


if __name__ == "__main__":
    unittest.main()

