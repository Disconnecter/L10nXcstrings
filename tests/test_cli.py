import unittest
import subprocess
import tempfile
import json
import os
import sys

SCRIPT_PATH = os.path.abspath("L10nXcstrings.py")

class TestCLI(unittest.TestCase):
    def test_basic_cli_run(self):
        data = {
            "hello": {
                "localizations": {
                    "en": {
                        "stringUnit": {
                            "value": "Hello %1$@",
                            "state": "translated"
                        }
                    }
                }
            }
        }

        with tempfile.TemporaryDirectory() as tmpdir:
            input_path = os.path.join(tmpdir, "Localizable.json")
            output_path = os.path.join(tmpdir, "L10n.swift")

            with open(input_path, "w") as f:
                json.dump(data, f)

            result = subprocess.run([
                sys.executable, SCRIPT_PATH,
                input_path,
                "--output", output_path,
                "--language", "en"
            ], capture_output=True)

            self.assertEqual(result.returncode, 0)
            self.assertTrue(os.path.exists(output_path))
