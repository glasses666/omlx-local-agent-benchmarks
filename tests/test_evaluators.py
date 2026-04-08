import base64
import tempfile
import unittest
from pathlib import Path

from omlx_benchmark.evaluators import image_file_to_data_uri


class EvaluatorTests(unittest.TestCase):
    def test_image_file_to_data_uri_uses_png_mime(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "sample.png"
            path.write_bytes(b"png-bytes")
            uri = image_file_to_data_uri(str(path))
            self.assertTrue(uri.startswith("data:image/png;base64,"))
            self.assertEqual(base64.b64decode(uri.split(",", 1)[1]), b"png-bytes")
