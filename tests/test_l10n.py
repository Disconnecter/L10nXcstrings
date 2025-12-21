import unittest
from unittest.mock import patch, mock_open, MagicMock
import os
import re
import json
import tempfile
from L10nXcstrings import (
    get_keys_and_strings_from_xcstrings,
    extract_placeholder_types,
    swiftify_key,
    find_used_keys_in_code,
    find_unused_keys,
    generate_strings,
)

class TestL10nXcstrings(unittest.TestCase):

    def test_get_keys_and_strings_from_xcstrings(self):
        mock_data = {
            "strings": {
                "key1": {"localizations": {"en": {"stringUnit": {"value": "Hello"}}}},
                "key2": {"localizations": {"en": {"stringUnit": {"value": "World"}}}},
            }
        }
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            result = get_keys_and_strings_from_xcstrings("mock_path")
        self.assertEqual(result, {"key1": "Hello", "key2": "World"})

    def test_extract_placeholder_types(self):
        string_value = "Hello %d, your score is %f"
        result = extract_placeholder_types(string_value)
        self.assertEqual(result, ["Int", "Double"])

    def test_extract_placeholder_types_length_modifiers(self):
        self.assertEqual(extract_placeholder_types("%lld"), ["Int64"])
        self.assertEqual(extract_placeholder_types("%llu"), ["UInt64"])

    def test_extract_placeholder_types_positional_gap(self):
        self.assertEqual(extract_placeholder_types("%2$@"), ["CVarArg", "String"])

    def test_swiftify_key(self):
        self.assertEqual(swiftify_key("hello_world"), "helloWorld")
        self.assertEqual(swiftify_key("hello-world"), "helloWorld")
        self.assertEqual(swiftify_key("hello.world"), "helloWorld")

    @patch("os.walk")
    def test_find_used_keys_in_code(self, mock_walk):
        mock_walk.return_value = [
            ("/mock_dir", ["subdir"], ["file1.swift"]),
        ]
        mock_file_content = "L10n.key1 L10n.key2"
        with patch("builtins.open", mock_open(read_data=mock_file_content)):
            result = find_used_keys_in_code(
                "/mock_dir", {"key1", "key2", "key3"}, "L10n", []
            )
        self.assertEqual(result, {"key1", "key2"})

    def test_find_used_keys_in_code_ignore_dirs(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            os.makedirs(os.path.join(temp_dir, "src", "build"), exist_ok=True)
            os.makedirs(os.path.join(temp_dir, "src", "other"), exist_ok=True)
            with open(
                os.path.join(temp_dir, "src", "build", "Ignored.swift"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write("L10n.ignored")
            with open(
                os.path.join(temp_dir, "src", "other", "Used.swift"),
                "w",
                encoding="utf-8",
            ) as f:
                f.write("L10n.used")

            result = find_used_keys_in_code(
                temp_dir, {"ignored", "used"}, "L10n", ["build"]
            )
            self.assertEqual(result, {"used"})

            result = find_used_keys_in_code(
                temp_dir, {"ignored", "used"}, "L10n", ["src/build"]
            )
            self.assertEqual(result, {"used"})

    @patch("os.path.exists", return_value=True)
    @patch("os.remove")
    @patch("builtins.open", new_callable=mock_open)
    def test_find_unused_keys(self, mock_open, mock_remove, mock_exists):
        args = MagicMock()
        args.source_dir = "/mock_dir"
        args.enum_name = "L10n"
        args.ignore_dirs = []
        args.output_unused = "unused.txt"
        swiftified_keys = {"key1": "key1", "key2": "key2", "key3": "key3"}

        with patch("L10nXcstrings.find_used_keys_in_code", return_value={"key1", "key2"}):
            result = find_unused_keys(args, swiftified_keys)

        self.assertEqual(result, {"key3"})
        mock_remove.assert_called_once_with("unused.txt")
        mock_open.assert_called_once_with("unused.txt", "w", encoding="utf-8")

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("L10nXcstrings.get_keys_and_strings_from_xcstrings")
    @patch("L10nXcstrings.find_unused_keys", return_value=set())
    def test_generate_strings(self, mock_unused, mock_keys, mock_open, mock_makedirs):
        mock_keys.return_value = {"key1": "Hello", "key2": "World"}
        args = MagicMock()
        args.input = "mock.xcstrings"
        args.output_swift = "Generated/Strings+Generated.swift"
        args.enum_name = "L10n"

        generate_strings(args)

        mock_makedirs.assert_called_once_with("Generated", exist_ok=True)
        mock_open.assert_called_once_with(
            "Generated/Strings+Generated.swift", "w", encoding="utf-8"
        )

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("L10nXcstrings.get_keys_and_strings_from_xcstrings")
    @patch("L10nXcstrings.find_unused_keys", return_value=set())
    def test_generate_strings_no_output_dir(self, mock_unused, mock_keys, mock_open, mock_makedirs):
        mock_keys.return_value = {"key1": "Hello"}
        args = MagicMock()
        args.input = "mock.xcstrings"
        args.output_swift = "Strings+Generated.swift"
        args.enum_name = "L10n"

        generate_strings(args)

        mock_makedirs.assert_not_called()

    def test_extract_placeholder_types_edge_cases(self):
        self.assertEqual(extract_placeholder_types("No placeholders"), [])
        self.assertEqual(extract_placeholder_types("%@ and %d"), ["String", "Int"])

if __name__ == "__main__":
    unittest.main()
