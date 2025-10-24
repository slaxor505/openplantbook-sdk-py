import asyncio
import unittest
from unittest.mock import patch

import aiohttp

from openplantbook_sdk import OpenPlantBookApi


class _RaisingSession:
    """Fake ClientSession whose get/post immediately raise a configured exception."""

    def __init__(self, *, raise_for_status=False, headers=None, exc_to_raise=None):
        self.raise_for_status = raise_for_status
        self.headers = headers or {}
        self._exc = exc_to_raise

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    # The production code uses async with session.get(...), so raising before
    # returning a context manager is fine and will be caught by the SDK.
    def get(self, *args, **kwargs):
        raise self._exc or RuntimeError("No exception configured")

    def post(self, *args, **kwargs):
        raise self._exc or RuntimeError("No exception configured")


async def _fake_get_token(api_self, *args, **kwargs):
    api_self.token = {"access_token": "TEST", "expires": "2099-01-01T00:00:00"}
    return True


def _too_many_redirects_exc():
    """Construct a TooManyRedirects instance with minimal required args across aiohttp versions.
    If construction fails (signature differences), fall back to a generic ClientError which is also handled by the SDK.
    """
    try:
        # aiohttp >=3.8 may require request_info and history positional args
        return aiohttp.TooManyRedirects(None, tuple())
    except TypeError:
        try:
            return aiohttp.TooManyRedirects(message="", history=(), request_info=None)
        except TypeError:
            return aiohttp.ClientError()


class TestErrorHandlingOffline(unittest.TestCase):
    def setUp(self):
        self.api = OpenPlantBookApi("id", "secret", base_url="https://example.invalid/api/v1")

    def _run_with_exc(self, exc):
        # Patch constructor to inject our exception into the fake session
        def _factory(**kwargs):
            return _RaisingSession(exc_to_raise=exc, **kwargs)

        return patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_factory)

    def test_detail_returns_none_on_timeout(self):
        with self._run_with_exc(aiohttp.ServerTimeoutError()), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            res = asyncio.run(self.api.async_plant_detail_get("pid"))
        self.assertIsNone(res)

    def test_detail_returns_none_on_redirects(self):
        with self._run_with_exc(_too_many_redirects_exc()), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            res = asyncio.run(self.api.async_plant_detail_get("pid"))
        self.assertIsNone(res)

    def test_detail_returns_none_on_client_error(self):
        with self._run_with_exc(aiohttp.ClientConnectionError()), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            res = asyncio.run(self.api.async_plant_detail_get("pid"))
        self.assertIsNone(res)

    def test_search_returns_none_on_errors(self):
        for exc in (aiohttp.ServerTimeoutError(), _too_many_redirects_exc(), aiohttp.ClientOSError()):
            with self.subTest(exc=exc):
                with self._run_with_exc(exc), \
                     patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
                    res = asyncio.run(self.api.async_plant_search("foo"))
                self.assertIsNone(res)

    def test_register_returns_none_on_timeout_or_redirect(self):
        for exc in (aiohttp.ServerTimeoutError(), _too_many_redirects_exc()):
            with self.subTest(exc=exc):
                with self._run_with_exc(exc), \
                     patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
                    res = asyncio.run(self.api.async_plant_instance_register({"A": "pid"}))
                self.assertIsNone(res)

    def test_upload_returns_none_on_client_error(self):
        with self._run_with_exc(aiohttp.ClientError()), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            ok = asyncio.run(self.api.async_plant_data_upload(jts_doc=_DummyJts()))
        self.assertIsNone(ok)

    def test_upload_returns_none_on_timeout_or_redirect(self):
        for exc in (aiohttp.ServerTimeoutError(), _too_many_redirects_exc()):
            with self.subTest(exc=exc):
                with self._run_with_exc(exc), \
                     patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
                    ok = asyncio.run(self.api.async_plant_data_upload(jts_doc=_DummyJts()))
                self.assertIsNone(ok)

    def test_detail_returns_none_on_generic_exception(self):
        # Trigger the broad except Exception path in async_plant_detail_get
        with self._run_with_exc(ValueError("boom")), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            res = asyncio.run(self.api.async_plant_detail_get("pid"))
        self.assertIsNone(res)


class _DummyJts:
    def toJSON(self):
        return {"series": []}

    def toJSONString(self):
        return "{}"


if __name__ == "__main__":
    unittest.main()
