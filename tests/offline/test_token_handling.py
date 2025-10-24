import asyncio
import unittest
from datetime import datetime, timedelta
from unittest.mock import patch

import aiohttp

from openplantbook_sdk import OpenPlantBookApi, MissingClientIdOrSecret


class _NeverCreateSession:
    """A stand-in for aiohttp.ClientSession that should never be instantiated.
    If it is, the test should fail immediately.
    """

    def __init__(self, *args, **kwargs):  # pragma: no cover - failure path
        raise AssertionError("Network session should not be created when token is cached")


class _FakeTokenResponse:
    def __init__(self, payload):
        self._payload = payload

    async def json(self):
        return self._payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _FakeTokenSession:
    def __init__(self, payload=None, exc=None, **kwargs):
        self._payload = payload
        self._exc = exc

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, url, data=None):
        if self._exc:
            raise self._exc
        return _FakeTokenResponse(self._payload)


def _too_many_redirects_exc():
    try:
        return aiohttp.TooManyRedirects(None, tuple())
    except TypeError:
        try:
            return aiohttp.TooManyRedirects(message="", history=(), request_info=None)
        except TypeError:
            return aiohttp.ClientError()


class TestTokenHandlingOffline(unittest.TestCase):
    """
    Offline tests for token handling logic. These tests do not perform network I/O.
    """

    def test_missing_client_id_or_secret_raises(self):
        api = OpenPlantBookApi("", "")
        with self.assertRaises(MissingClientIdOrSecret):
            asyncio.run(api._async_get_token())

    def test_cached_token_skips_network(self):
        api = OpenPlantBookApi("id", "secret")
        # Simulate a valid token that expires in > 5 minutes
        api.token = {
            "access_token": "CACHED",
            "expires": (datetime.now() + timedelta(minutes=10)).isoformat(),
        }
        # Ensure no ClientSession is ever constructed when token is fresh
        with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_NeverCreateSession):
            ok = asyncio.run(api._async_get_token())
        self.assertTrue(ok)

    def test_successful_token_fetch_sets_token(self):
        api = OpenPlantBookApi("id", "secret")
        payload = {"access_token": "ABC", "expires_in": 3600}

        def _factory(**kwargs):
            return _FakeTokenSession(payload=payload, **kwargs)

        with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_factory):
            ok = asyncio.run(api._async_get_token())
        self.assertTrue(ok)
        self.assertIsNotNone(api.token)
        self.assertEqual(api.token.get("access_token"), "ABC")
        self.assertIn("expires", api.token)

    def test_permission_error_is_raised_when_no_access_token(self):
        api = OpenPlantBookApi("id", "secret")
        payload = {"token_type": "bearer"}  # no access_token

        def _factory(**kwargs):
            return _FakeTokenSession(payload=payload, **kwargs)

        with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_factory):
            with self.assertRaises(PermissionError):
                asyncio.run(api._async_get_token())

    def test_specific_exceptions_are_reraised(self):
        api = OpenPlantBookApi("id", "secret")
        for exc in (aiohttp.ServerTimeoutError(), _too_many_redirects_exc(), aiohttp.ClientError()):
            with self.subTest(exc=exc):
                def _factory(**kwargs):
                    return _FakeTokenSession(exc=exc, **kwargs)
                with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_factory):
                    with self.assertRaises(type(exc)):
                        asyncio.run(api._async_get_token())


if __name__ == "__main__":
    unittest.main()
