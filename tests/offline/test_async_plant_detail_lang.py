import asyncio
import unittest
from unittest.mock import patch

from openplantbook_sdk import OpenPlantBookApi


class _FakeResponse:
    def __init__(self, url, params):
        self.url = url
        self._params = params
        self.status = 200

    async def json(self):
        # Minimal JSON body; content is not asserted in this test
        return {"ok": True}

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeSession:
    # Keep a reference to the last created instance for assertions
    last_created = None

    def __init__(self, *, raise_for_status=False, headers=None):
        self.raise_for_status = raise_for_status
        self.headers = headers or {}
        self.last_get_url = None
        self.last_get_params = None
        _FakeSession.last_created = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None):
        # Record call for assertions and return an async context manager
        self.last_get_url = url
        self.last_get_params = params
        return _FakeResponse(url, params)


async def _fake_get_token(api_self, *args, **kwargs):
    # Inject a dummy token so the method can proceed to the GET request
    api_self.token = {"access_token": "TEST_TOKEN", "expires": "2099-01-01T00:00:00"}
    return True


class TestAsyncPlantDetailLangOffline(unittest.TestCase):
    """
    Offline tests for async_plant_detail_get ensuring the 'lang' query parameter
    is forwarded correctly to aiohttp.ClientSession.get(..., params=...).

    These tests do not perform network I/O and do not require real credentials.
    """

    def setUp(self):
        # Use a dummy base_url to make it obvious this is offline
        self.api = OpenPlantBookApi("id", "secret", base_url="https://example.invalid/api/v1")

    def test_forwards_lang_param_when_provided(self):
        with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_FakeSession), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            asyncio.run(self.api.async_plant_detail_get("abelia chinensis", lang="de"))

        sess = _FakeSession.last_created
        self.assertIsNotNone(sess, "Fake session was not created")
        # Assert that the Authorization header is set using our injected token
        self.assertIn("Authorization", sess.headers)
        self.assertTrue(sess.headers["Authorization"].startswith("Bearer "))
        # Assert that the request URL targets the expected endpoint
        self.assertTrue(sess.last_get_url.endswith("/plant/detail/abelia chinensis"))
        # Critical assertion: 'lang' param is forwarded
        self.assertEqual(sess.last_get_params, {"lang": "de"})

    def test_omits_lang_param_when_none(self):
        with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_FakeSession), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            asyncio.run(self.api.async_plant_detail_get("abelia chinensis", lang=None))

        sess = _FakeSession.last_created
        self.assertIsNotNone(sess, "Fake session was not created")
        # When lang is None, the SDK should pass params=None
        self.assertIsNone(sess.last_get_params)


if __name__ == "__main__":
    unittest.main()
