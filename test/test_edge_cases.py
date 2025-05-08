import unittest
import tempfile
import os
import json
from unittest.mock import patch
from L10nXcstrings import extract_localized_strings, format_string_placeholders, main

class TestEdgeCases(unittest.TestCase):
    def test_missing_localization(self):
        d = {
            "title": {
                "localizations": {
                    "fr": {
                        "stringUnit": {
                            "value": "Bonjour",
                            "state": "translated"
                        }
                    }
                }
            }
        }
        self.assertEqual(extract_localized_strings(d, "en"), {})

    def test_untranslated_string(self):
        d = {
            "title": {
                "localizations": {
                    "en": {
                        "stringUnit": {
                            "value": "Untranslated",
                            "state": "needs-review"
                        }
                    }
                }
            }
        }
        self.assertEqual(extract_localized_strings(d, "en"), {})

    def test_invalid_placeholder_format(self):
        s = "Invalid %d format"
        self.assertEqual(format_string_placeholders(s), [])

    def test_malformed_input_json(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            bad_path = os.path.join(tmpdir, "bad.json")
            with open(bad_path, "w") as f:
                f.write("not a json file")

            output_path = os.path.join(tmpdir, "out.swift")

            with patch("sys.argv", ["L10nXcstrings.py", bad_path, "--output", output_path]):
                with self.assertRaises(SystemExit):
                    main()
