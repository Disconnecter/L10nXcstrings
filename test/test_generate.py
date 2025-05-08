import unittest
import tempfile
import os
from L10nXcstrings import generate_code

class TestGenerateCode(unittest.TestCase):
    def test_generate_output_file(self):
        data = {
            "greet": {
                "value": "Hi %1$@",
                "placeholders": ["%1$@"]
            },
            "count": {
                "value": "Count: %1$li",
                "placeholders": ["%1$li"]
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            path = os.path.join(tmpdir, "L10n.swift")
            generate_code(data, path)

            self.assertTrue(os.path.exists(path))
            with open(path, "r") as f:
                content = f.read()
                self.assertIn("enum L10n", content)
                self.assertIn("case greet(String)", content)
                self.assertIn("case count(Int)", content)
