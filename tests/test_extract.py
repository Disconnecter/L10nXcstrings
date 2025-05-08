import unittest
from L10nXcstrings import extract_localized_strings, format_string_placeholders

class TestExtract(unittest.TestCase):
    def test_extract_localized_strings(self):
        input_dict = {
            "test.key": {
                "localizations": {
                    "en": {
                        "stringUnit": {
                            "value": "Hi %1$@!",
                            "state": "translated"
                        }
                    }
                }
            }
        }
        result = extract_localized_strings(input_dict, "en")
        self.assertEqual(result, {
            "test.key": {
                "value": "Hi %1$@!",
                "placeholders": ["%1$@"]
            }
        })

    def test_format_placeholders(self):
        s = "Value %1$@ and %2$li."
        self.assertEqual(format_string_placeholders(s), ["%1$@", "%2$li"])

    def test_format_no_placeholders(self):
        s = "No placeholders here."
        self.assertEqual(format_string_placeholders(s), [])
