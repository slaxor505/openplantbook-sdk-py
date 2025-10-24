import asyncio
import unittest
from unittest.mock import patch

from openplantbook_sdk import OpenPlantBookApi
from copy import deepcopy


class _FakeResponse:
    def __init__(self, url, params=None, json_payload=None, status=200):
        self.url = url
        self._params = params
        self._json_payload = json_payload
        self.status = status
        # emulate requests.Response.ok used in async_plant_data_upload
        self.ok = 200 <= status < 400

    async def json(self, content_type=None):  # content_type accepted for upload code path
        # Return echo payload if provided, otherwise a minimal JSON body
        return self._json_payload if self._json_payload is not None else {"ok": True}

    def raise_for_status(self):
        # No-op for status < 400 in these offline tests
        if self.status and self.status >= 400:
            raise AssertionError(f"Unexpected status in offline test: {self.status}")

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
        # GET tracking
        self.last_get_url = None
        self.last_get_params = None
        self.last_get_kwargs = None
        # POST tracking
        self.last_post_url = None
        self.last_post_params = None
        self.last_post_json = None
        self.last_post_kwargs = None
        _FakeSession.last_created = self

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def get(self, url, params=None, **kwargs):
        # Record call for assertions and return an async context manager
        self.last_get_url = url
        self.last_get_params = params
        self.last_get_kwargs = kwargs
        return _FakeResponse(url, params=params)

    def post(self, url, json=None, params=None, raise_for_status=False, **kwargs):
        # Record call for assertions and return an async context manager
        self.last_post_url = url
        self.last_post_params = params
        self.last_post_json = json
        self.last_post_kwargs = kwargs
        # Echo back the posted JSON so tests can inspect the effective payload
        # Use deepcopy to snapshot the payload at call time so later mutations don't affect earlier responses.
        echo_payload = {"echo": deepcopy(json)}
        return _FakeResponse(url, params=params, json_payload=echo_payload, status=200)


async def _fake_get_token(api_self, *args, **kwargs):
    # Inject a dummy token so methods can proceed to their HTTP calls
    api_self.token = {"access_token": "TEST_TOKEN", "expires": "2099-01-01T00:00:00"}
    return True


class _FakeJtsDocument:
    def __init__(self, payload=None):
        self._payload = payload or {"series": []}

    def toJSON(self):
        return self._payload

    def toJSONString(self):
        return "{}"


class TestPassThroughParamsOffline(unittest.TestCase):
    """
    Offline tests for pass-through params and request kwargs across SDK methods.

    These tests do not perform network I/O and do not require real credentials.
    """

    def setUp(self):
        # Use a dummy base_url to make it obvious this is offline
        self.api = OpenPlantBookApi("id", "secret", base_url="https://example.invalid/api/v1")

    def test_detail_merges_and_overrides_lang_and_kwargs(self):
        with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_FakeSession), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            asyncio.run(self.api.async_plant_detail_get(
                "abelia chinensis",
                lang="de",
                params={"lang": "en", "page": "2"},
                request_kwargs={"timeout": 7}
            ))

        sess = _FakeSession.last_created
        self.assertIsNotNone(sess, "Fake session was not created")
        # Authorization header should be set using the injected token
        self.assertIn("Authorization", sess.headers)
        self.assertTrue(sess.headers["Authorization"].startswith("Bearer "))
        # Request URL targets the expected endpoint
        self.assertTrue(sess.last_get_url.endswith("/plant/detail/abelia chinensis"))
        # 'lang' from explicit arg overrides value in params; other params are preserved
        self.assertEqual(sess.last_get_params, {"lang": "de", "page": "2"})
        # request_kwargs forwarded to session.get
        self.assertEqual(sess.last_get_kwargs.get("timeout"), 7)

    def test_search_forwards_params_and_kwargs(self):
        with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_FakeSession), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            asyncio.run(self.api.async_plant_search(
                "foo",
                params={"page": "3"},
                request_kwargs={"allow_redirects": False}
            ))

        sess = _FakeSession.last_created
        self.assertIsNotNone(sess, "Fake session was not created")
        # URL keeps alias in the path/query string
        self.assertIn("/plant/search?alias=foo", sess.last_get_url)
        self.assertEqual(sess.last_get_params, {"page": "3"})
        self.assertEqual(sess.last_get_kwargs.get("allow_redirects"), False)

    def test_register_merges_extra_and_forwards(self):
        with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_FakeSession), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            res = asyncio.run(self.api.async_plant_instance_register(
                sensor_pid_map={"Sensor-1": "abelia chinensis"},
                location_country="AU",
                extra_json={"location_name": "Sydney"},
                params={"confirm": "1"},
                request_kwargs={"timeout": 5}
            ))

        sess = _FakeSession.last_created
        self.assertIsNotNone(sess, "Fake session was not created")
        # Query params and request kwargs are forwarded
        self.assertEqual(sess.last_post_params, {"confirm": "1"})
        self.assertEqual(sess.last_post_kwargs.get("timeout"), 5)
        # Payload contains merged fields and excludes None-valued defaults
        payload = sess.last_post_json
        self.assertIn("location_country", payload)
        self.assertIn("location_name", payload)  # from extra_json
        self.assertIn("custom_id", payload)
        self.assertIn("pid", payload)
        self.assertNotIn("location_by_IP", payload)  # default None should be removed
        self.assertNotIn("location_lon", payload)
        self.assertNotIn("location_lat", payload)
        # Method returns list with echo of our request payload
        self.assertIsInstance(res, list)
        self.assertTrue(any("echo" in item for item in res))

    def test_upload_dry_run_param_override_and_kwargs(self):
        fake_doc = _FakeJtsDocument(payload={"series": []})
        with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_FakeSession), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            ok = asyncio.run(self.api.async_plant_data_upload(
                fake_doc,
                dry_run=False,
                params={"dry_run": "true", "batch_id": "123"},
                request_kwargs={"ssl": False}
            ))

        sess = _FakeSession.last_created
        self.assertIsNotNone(sess, "Fake session was not created")
        # Caller-provided params override the SDK-built dry_run value and are forwarded
        self.assertEqual(sess.last_post_params, {"dry_run": "true", "batch_id": "123"})
        # request_kwargs forwarded to session.post
        self.assertEqual(sess.last_post_kwargs.get("ssl"), False)
        # SDK returns result.ok which our fake sets to True
        self.assertTrue(ok)

    def test_register_handles_multiple_items_returns_all(self):
        with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_FakeSession), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            res = asyncio.run(self.api.async_plant_instance_register(
                sensor_pid_map={"A": "pid1", "B": "pid2"},
                location_country="AU"
            ))
        # Expect two results echoing our two posts
        self.assertEqual(len(res), 2)
        self.assertEqual(res[0]["echo"]["custom_id"], "A")
        self.assertEqual(res[0]["echo"]["pid"], "pid1")
        self.assertEqual(res[1]["echo"]["custom_id"], "B")
        self.assertEqual(res[1]["echo"]["pid"], "pid2")


if __name__ == "__main__":
    unittest.main()
