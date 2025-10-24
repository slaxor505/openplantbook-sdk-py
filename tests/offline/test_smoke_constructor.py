import unittest

from openplantbook_sdk import OpenPlantBookApi


class TestSmokeConstructor(unittest.TestCase):
    def test_import_and_basic_attributes(self):
        api = OpenPlantBookApi("id", "secret", base_url="https://example.invalid")
        self.assertEqual(api.client_id, "id")
        self.assertEqual(api.secret, "secret")
        self.assertEqual(api._PLANTBOOK_BASEURL, "https://example.invalid")


if __name__ == "__main__":
    unittest.main()
