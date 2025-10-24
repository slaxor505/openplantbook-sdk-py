import asyncio
import unittest
from unittest.mock import patch

from openplantbook_sdk import OpenPlantBookApi, ValidationError


class _FakeResponse:
    def __init__(self, status=400, body=None):
        self.status = status
        self._body = body or {"type": "validation_error", "errors": {"field": ["msg"]}}

    async def json(self, content_type=None):  # signature used by sdk
        return self._body

    def raise_for_status(self):
        # No-op: sdk raises ValidationError before calling this when status==400
        return None

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


class _SessionReturnsValidationError:
    def __init__(self, *args, **kwargs):
        pass

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def post(self, *args, **kwargs):
        return _FakeResponse()


async def _fake_get_token(api_self, *args, **kwargs):
    api_self.token = {"access_token": "TEST", "expires": "2099-01-01T00:00:00"}
    return True


class TestValidationErrorOffline(unittest.TestCase):
    def setUp(self):
        self.api = OpenPlantBookApi("id", "secret", base_url="https://example.invalid/api/v1")

    def test_register_raises_validation_error_and_exposes_errors(self):
        with patch("openplantbook_sdk.sdk.aiohttp.ClientSession", new=_SessionReturnsValidationError), \
             patch.object(OpenPlantBookApi, "_async_get_token", new=_fake_get_token):
            with self.assertRaises(ValidationError) as ctx:
                asyncio.run(self.api.async_plant_instance_register({"A": "pid"}))
        err = ctx.exception
        self.assertTrue(hasattr(err, "errors"))
        self.assertIsInstance(err.errors, dict)
        # __str__ includes error details
        self.assertIn("API returned", str(err))


if __name__ == "__main__":
    unittest.main()
