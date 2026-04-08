import unittest

from omlx_benchmark.admin_api import OMLXAdminClient


class AdminApiTests(unittest.TestCase):
    def test_client_starts_logged_out(self) -> None:
        client = OMLXAdminClient(base_url="http://127.0.0.1:8000", api_key="test")
        self.assertFalse(client._logged_in)
