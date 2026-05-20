import contextlib
import io
import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest
from unittest.mock import MagicMock, mock_open, patch

from L10nXcstrings import (
    build_swiftified_keys,
    extract_placeholder_types,
    find_unused_keys,
    find_used_keys_in_code,
    generate_strings,
    get_keys_and_strings_from_xcstrings,
    get_localized_strings_from_xcstrings,
    swiftify_key,
)


def darwin_swiftc_or_skip(test_case):
    if sys.platform != "darwin":
        test_case.skipTest("Swift Foundation localization tests require Darwin")
    swiftc = shutil.which("swiftc")
    if not swiftc:
        test_case.skipTest("swiftc is not installed")
    return swiftc


def run_checked(test_case, command, **kwargs):
    result = subprocess.run(command, capture_output=True, text=True, **kwargs)
    if result.returncode != 0:
        test_case.fail(
            "\n".join(
                [
                    f"Command failed with exit code {result.returncode}: {command}",
                    "stdout:",
                    result.stdout,
                    "stderr:",
                    result.stderr,
                ]
            )
        )
    return result


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

    def test_get_keys_and_strings_fails_for_missing_source_language(self):
        mock_data = {
            "sourceLanguage": "uk",
            "strings": {
                "key1": {"localizations": {"uk": {"stringUnit": {"value": "Pryvit"}}}},
                "key2": {"localizations": {"en": {"stringUnit": {"value": "World"}}}},
            },
        }
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            with self.assertRaisesRegex(ValueError, "key2"):
                get_keys_and_strings_from_xcstrings("mock_path")

    def test_get_keys_and_strings_allows_missing_when_requested(self):
        mock_data = {
            "sourceLanguage": "uk",
            "strings": {
                "key1": {"localizations": {"uk": {"stringUnit": {"value": "Pryvit"}}}},
                "key2": {"localizations": {"en": {"stringUnit": {"value": "World"}}}},
            },
        }
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            with contextlib.redirect_stderr(io.StringIO()):
                result = get_keys_and_strings_from_xcstrings(
                    "mock_path",
                    allow_missing=True,
                )
        self.assertEqual(result, {"key1": "Pryvit"})

    def test_get_keys_and_strings_accepts_language_override(self):
        mock_data = {
            "sourceLanguage": "uk",
            "strings": {
                "key1": {
                    "localizations": {
                        "uk": {"stringUnit": {"value": "Pryvit"}},
                        "en": {"stringUnit": {"value": "Hello"}},
                    }
                },
            },
        }
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            result = get_keys_and_strings_from_xcstrings("mock_path", language="en")
        self.assertEqual(result, {"key1": "Hello"})

    def test_get_localized_strings_reads_variations(self):
        mock_data = {
            "sourceLanguage": "en",
            "strings": {
                "files.count": {
                    "localizations": {
                        "en": {
                            "variations": {
                                "plural": {
                                    "one": {"stringUnit": {"value": "%d file"}},
                                    "other": {"stringUnit": {"value": "%d files"}},
                                }
                            }
                        }
                    }
                },
            },
        }
        with patch("builtins.open", mock_open(read_data=json.dumps(mock_data))):
            result = get_localized_strings_from_xcstrings("mock_path")
        self.assertEqual(result["files.count"].display_value, "%d file")
        self.assertEqual(result["files.count"].values, ("%d file", "%d files"))

    def test_get_localized_strings_reads_xcode_fixture(self):
        fixture_path = os.path.join(
            os.path.dirname(__file__),
            "fixtures",
            "Localizable.xcstrings",
        )

        result = get_localized_strings_from_xcstrings(fixture_path)

        self.assertEqual(result["fixture.title"].display_value, "Fixture Title")
        self.assertEqual(
            result["fixture.items.count"].values,
            ("%d item", "%d items"),
        )

    def test_extract_placeholder_types(self):
        string_value = "Hello %d, your score is %f"
        result = extract_placeholder_types(string_value)
        self.assertEqual(result, ["Int", "Double"])

    def test_extract_placeholder_types_length_modifiers(self):
        self.assertEqual(extract_placeholder_types("%lld"), ["Int64"])
        self.assertEqual(extract_placeholder_types("%llu"), ["UInt64"])

    def test_extract_placeholder_types_positional_gap(self):
        with self.assertRaises(ValueError):
            extract_placeholder_types("%2$@")

    def test_extract_placeholder_types_rejects_zero_position(self):
        with self.assertRaisesRegex(ValueError, "1-based"):
            extract_placeholder_types("%0$@")

    def test_extract_placeholder_types_positionals(self):
        self.assertEqual(extract_placeholder_types("%2$@ %1$d"), ["Int", "String"])
        self.assertEqual(extract_placeholder_types("%1$@ %1$@"), ["String"])

    def test_extract_placeholder_types_plural_token(self):
        self.assertEqual(extract_placeholder_types("%#@items@"), ["CVarArg"])
        self.assertEqual(extract_placeholder_types("%1$#@items@"), ["CVarArg"])

    def test_extract_placeholder_types_mixed_positionals(self):
        with self.assertRaises(ValueError):
            extract_placeholder_types("%2$@ %d")

    def test_extract_placeholder_types_rejects_conflicting_positionals(self):
        with self.assertRaisesRegex(ValueError, "Conflicting types"):
            extract_placeholder_types("%1$@ %1$d")

    def test_extract_placeholder_types_rejects_ambiguous_bare_percent(self):
        with self.assertRaisesRegex(ValueError, "escape literal percent"):
            extract_placeholder_types("Progress 100%complete")

    def test_extract_placeholder_types_rejects_c_string_placeholder(self):
        with self.assertRaisesRegex(ValueError, "use %@"):
            extract_placeholder_types("Name %s")

    def test_extract_placeholder_types_allows_adjacent_units_for_common_placeholders(self):
        self.assertEqual(extract_placeholder_types("%dkg %@Name"), ["Int", "String"])

    def test_swiftify_key(self):
        self.assertEqual(swiftify_key("hello_world"), "helloWorld")
        self.assertEqual(swiftify_key("hello-world"), "helloWorld")
        self.assertEqual(swiftify_key("hello.world"), "helloWorld")
        self.assertEqual(swiftify_key("1foo"), "_1foo")
        self.assertEqual(swiftify_key("login title"), "loginTitle")
        self.assertEqual(swiftify_key("class"), "class")

    def test_swiftify_key_adds_stable_names_for_non_ascii_keys(self):
        self.assertRegex(swiftify_key("кнопка.назва"), r"^key[a-f0-9A-F]{8}$")
        self.assertRegex(swiftify_key("title.назва"), r"^title[a-f0-9A-F]{8}$")

    def test_build_swiftified_keys_rejects_collisions(self):
        with self.assertRaisesRegex(ValueError, "Swift key collisions"):
            build_swiftified_keys(["foo.bar", "foo_bar"])

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
            ) as file:
                file.write("L10n.ignored")
            with open(
                os.path.join(temp_dir, "src", "other", "Used.swift"),
                "w",
                encoding="utf-8",
            ) as file:
                file.write("L10n.used")

            result = find_used_keys_in_code(
                temp_dir, {"ignored", "used"}, "L10n", ["build"]
            )
            self.assertEqual(result, {"used"})

            result = find_used_keys_in_code(
                temp_dir, {"ignored", "used"}, "L10n", ["src/build"]
            )
        self.assertEqual(result, {"used"})

    def test_find_used_keys_ignores_comments_and_strings(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = os.path.join(temp_dir, "Used.swift")
            with open(source_path, "w", encoding="utf-8") as file:
                file.write(
                    "\n".join(
                        [
                            "// L10n.commented",
                            'let text = "L10n.inString"',
                            "let title = L10n.real",
                            "let keyword = L10n.`class`",
                        ]
                    )
                )

            result = find_used_keys_in_code(
                temp_dir,
                {"commented", "inString", "real", "class"},
                "L10n",
                [],
            )
            self.assertEqual(result, {"real", "class"})

    def test_find_used_keys_preserves_string_interpolation(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = os.path.join(temp_dir, "Used.swift")
            with open(source_path, "w", encoding="utf-8") as file:
                file.write(
                    "\n".join(
                        [
                            'let title = "Title: \\(L10n.interpolated)"',
                            'let raw = #"Title: \\#(L10n.rawInterpolated)"#',
                            'let plain = "L10n.inPlainString"',
                        ]
                    )
                )

            result = find_used_keys_in_code(
                temp_dir,
                {"interpolated", "rawInterpolated", "inPlainString"},
                "L10n",
                [],
            )
            self.assertEqual(result, {"interpolated", "rawInterpolated"})

    def test_find_used_keys_ignores_nested_block_comments(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = os.path.join(temp_dir, "Used.swift")
            with open(source_path, "w", encoding="utf-8") as file:
                file.write(
                    "\n".join(
                        [
                            "/*",
                            "L10n.outerComment",
                            "/* L10n.innerComment */",
                            "*/",
                            "let title = L10n.real",
                        ]
                    )
                )

            result = find_used_keys_in_code(
                temp_dir,
                {"outerComment", "innerComment", "real"},
                "L10n",
                [],
            )
            self.assertEqual(result, {"real"})

    def test_find_used_keys_detects_typed_shorthand_cases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = os.path.join(temp_dir, "Used.swift")
            with open(source_path, "w", encoding="utf-8") as file:
                file.write(
                    "\n".join(
                        [
                            "let selected: L10n = .inferred",
                            "switch selected {",
                            "case .switched:",
                            "  break",
                            "case .unused:",
                            "  break",
                            "}",
                            "switch other { case .foreign: break }",
                        ]
                    )
                )

            result = find_used_keys_in_code(
                temp_dir,
                {"inferred", "switched", "unused", "foreign"},
                "L10n",
                [],
            )
            self.assertEqual(result, {"inferred", "switched", "unused"})

    def test_find_used_keys_detects_native_localization_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = os.path.join(temp_dir, "Used.swift")
            with open(source_path, "w", encoding="utf-8") as file:
                file.write(
                    "\n".join(
                        [
                            'let title = String(localized: "login.title")',
                            'let subtitle = NSLocalizedString("screen.subtitle", comment: "")',
                            'let view = Text("screen.body")',
                            'let button = Button("screen.button") {}',
                            'let toggle = Toggle("screen.toggle", isOn: .constant(true))',
                            'let label = Label("screen.label", systemImage: "star")',
                            'let titled = view.navigationTitle("screen.nav")',
                            '// NSLocalizedString("commented.key", comment: "")',
                        ]
                    )
                )

            result = find_used_keys_in_code(
                temp_dir,
                {
                    "loginTitle",
                    "screenSubtitle",
                    "screenBody",
                    "screenButton",
                    "screenToggle",
                    "screenLabel",
                    "screenNav",
                    "commentedKey",
                },
                "L10n",
                [],
                {
                    "login.title": "loginTitle",
                    "screen.subtitle": "screenSubtitle",
                    "screen.body": "screenBody",
                    "screen.button": "screenButton",
                    "screen.toggle": "screenToggle",
                    "screen.label": "screenLabel",
                    "screen.nav": "screenNav",
                    "commented.key": "commentedKey",
                },
            )
            self.assertEqual(
                result,
                {
                    "loginTitle",
                    "screenSubtitle",
                    "screenBody",
                    "screenButton",
                    "screenToggle",
                    "screenLabel",
                    "screenNav",
                },
            )

    def test_find_used_keys_supports_custom_native_localization_calls(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = os.path.join(temp_dir, "Used.swift")
            with open(source_path, "w", encoding="utf-8") as file:
                file.write('let chip = ChipTitle("custom.key").toolbarTitle("custom.member")')

            result = find_used_keys_in_code(
                temp_dir,
                {"customKey", "customMember"},
                "L10n",
                [],
                {
                    "custom.key": "customKey",
                    "custom.member": "customMember",
                },
                localized_calls=["ChipTitle"],
                localized_members=["toolbarTitle"],
            )

            self.assertEqual(result, {"customKey", "customMember"})

    def test_find_used_keys_ignores_nested_switch_shorthand_cases(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            source_path = os.path.join(temp_dir, "Used.swift")
            with open(source_path, "w", encoding="utf-8") as file:
                file.write(
                    "\n".join(
                        [
                            "let selected: L10n = .inferred",
                            "switch selected {",
                            "case .topLevel:",
                            "  switch other { case .nestedForeign: break }",
                            "}",
                        ]
                    )
                )

            result = find_used_keys_in_code(
                temp_dir,
                {"inferred", "topLevel", "nestedForeign"},
                "L10n",
                [],
            )

            self.assertEqual(result, {"inferred", "topLevel"})

    @patch("os.path.exists", return_value=True)
    @patch("os.remove")
    @patch("builtins.open", new_callable=mock_open)
    def test_find_unused_keys(self, mocked_open, mock_remove, mock_exists):
        args = MagicMock()
        args.source_dir = "/mock_dir"
        args.enum_name = "L10n"
        args.ignore_dirs = []
        args.output_unused = "unused.txt"
        swiftified_keys = {"key1": "key1", "key2": "key2", "key3": "key3"}

        with patch("l10n_xcstrings.codegen.find_used_keys_in_code", return_value={"key1", "key2"}):
            with contextlib.redirect_stdout(io.StringIO()):
                result = find_unused_keys(args, swiftified_keys)

        self.assertEqual(result, {"key3"})
        mock_remove.assert_called_once_with("unused.txt")
        mocked_open.assert_called_once_with("unused.txt", "w", encoding="utf-8")

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("l10n_xcstrings.cli.get_localized_strings_from_xcstrings")
    @patch("l10n_xcstrings.codegen.find_unused_keys", return_value=set())
    def test_generate_strings(self, mock_unused, mock_keys, mocked_open, mock_makedirs):
        mock_keys.return_value = {"key1": "Hello", "key2": "World"}
        args = MagicMock()
        args.input = "mock.xcstrings"
        args.output_swift = "Generated/Strings+Generated.swift"
        args.enum_name = "L10n"
        args.language = None
        args.allow_missing = False

        with contextlib.redirect_stdout(io.StringIO()):
            generate_strings(args)

        mock_makedirs.assert_called_once_with("Generated", exist_ok=True)
        mocked_open.assert_called_once_with(
            "Generated/Strings+Generated.swift", "w", encoding="utf-8"
        )

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("l10n_xcstrings.cli.get_localized_strings_from_xcstrings")
    @patch("l10n_xcstrings.codegen.find_unused_keys", return_value=set())
    def test_generate_strings_no_output_dir(
        self, mock_unused, mock_keys, mocked_open, mock_makedirs
    ):
        mock_keys.return_value = {"key1": "Hello"}
        args = MagicMock()
        args.input = "mock.xcstrings"
        args.output_swift = "Strings+Generated.swift"
        args.enum_name = "L10n"
        args.language = None
        args.allow_missing = False

        with contextlib.redirect_stdout(io.StringIO()):
            generate_strings(args)

        mock_makedirs.assert_not_called()

    def test_extract_placeholder_types_edge_cases(self):
        self.assertEqual(extract_placeholder_types("No placeholders"), [])
        self.assertEqual(extract_placeholder_types("%@ and %d"), ["String", "Int"])
        self.assertEqual(extract_placeholder_types("Progress 100%% done"), [])
        self.assertEqual(extract_placeholder_types("%c %p"), ["Int", "UInt"])

    def test_generate_strings_writes_expected_swift_content(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            xcstrings_path = os.path.join(temp_dir, "Localizable.xcstrings")
            output_path = os.path.join(temp_dir, "Generated.swift")
            unused_path = os.path.join(temp_dir, "Unused.txt")
            data = {
                "sourceLanguage": "en",
                "strings": {
                    "class": {"localizations": {"en": {"stringUnit": {"value": "Class"}}}},
                    "count.value": {"localizations": {"en": {"stringUnit": {"value": "Count %d"}}}},
                    "progress": {
                        "localizations": {
                            "en": {"stringUnit": {"value": "Progress 100%% done"}}
                        }
                    },
                    "quote\"key": {"localizations": {"en": {"stringUnit": {"value": "Quoted"}}}},
                },
            }
            with open(xcstrings_path, "w", encoding="utf-8") as file:
                json.dump(data, file)

            args = MagicMock()
            args.input = xcstrings_path
            args.output_swift = output_path
            args.output_unused = unused_path
            args.source_dir = temp_dir
            args.enum_name = "L10n"
            args.ignore_dirs = []
            args.language = None
            args.allow_missing = False

            with contextlib.redirect_stdout(io.StringIO()):
                generate_strings(args)

            with open(output_path, encoding="utf-8") as file:
                generated = file.read()
            with open(unused_path, encoding="utf-8") as file:
                unused = file.read().splitlines()

            self.assertIn("public static var `class`: String", generated)
            self.assertIn("public static func countValue(_ p1: Int) -> String", generated)
            self.assertIn("public static var progress: String", generated)
            self.assertNotIn("progress(_ p1:", generated)
            self.assertIn('return tr(key: "quote\\"key")', generated)
            self.assertEqual(unused, ["class", "count.value", "progress", 'quote"key'])

    def test_generate_strings_reports_key_for_bad_placeholder(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            xcstrings_path = os.path.join(temp_dir, "Localizable.xcstrings")
            output_path = os.path.join(temp_dir, "Generated.swift")
            unused_path = os.path.join(temp_dir, "Unused.txt")
            data = {
                "sourceLanguage": "en",
                "strings": {
                    "bad.percent": {
                        "localizations": {
                            "en": {"stringUnit": {"value": "Progress 100%complete"}}
                        }
                    },
                },
            }
            with open(xcstrings_path, "w", encoding="utf-8") as file:
                json.dump(data, file)

            args = MagicMock()
            args.input = xcstrings_path
            args.output_swift = output_path
            args.output_unused = unused_path
            args.source_dir = temp_dir
            args.enum_name = "L10n"
            args.ignore_dirs = []
            args.language = None
            args.allow_missing = False

            with self.assertRaisesRegex(ValueError, "bad.percent"):
                generate_strings(args)

    def test_generate_strings_supports_table_bundle_and_variation_placeholders(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            xcstrings_path = os.path.join(temp_dir, "Localizable.xcstrings")
            output_path = os.path.join(temp_dir, "Generated.swift")
            unused_path = os.path.join(temp_dir, "Unused.txt")
            data = {
                "sourceLanguage": "en",
                "strings": {
                    "files.count": {
                        "localizations": {
                            "en": {
                                "stringUnit": {"value": "%#@items@"},
                                "variations": {
                                    "plural": {
                                        "one": {"stringUnit": {"value": "%d file"}},
                                        "other": {"stringUnit": {"value": "%d files"}},
                                    }
                                },
                            }
                        }
                    },
                },
            }
            with open(xcstrings_path, "w", encoding="utf-8") as file:
                json.dump(data, file)

            args = MagicMock()
            args.input = xcstrings_path
            args.output_swift = output_path
            args.output_unused = unused_path
            args.source_dir = temp_dir
            args.enum_name = "L10n"
            args.ignore_dirs = []
            args.language = None
            args.allow_missing = False
            args.table_name = "Feature"
            args.bundle = "Bundle.module"

            with contextlib.redirect_stdout(io.StringIO()):
                generate_strings(args)

            with open(output_path, encoding="utf-8") as file:
                generated = file.read()

            self.assertIn("public static func filesCount(_ p1: Int) -> String", generated)
            self.assertIn('tableName: "Feature"', generated)
            self.assertIn("bundle: Bundle.module", generated)

    def test_cli_generates_files(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            xcstrings_path = os.path.join(temp_dir, "Localizable.xcstrings")
            output_path = os.path.join(temp_dir, "Generated.swift")
            unused_path = os.path.join(temp_dir, "Unused.txt")
            source_path = os.path.join(temp_dir, "Used.swift")
            with open(xcstrings_path, "w", encoding="utf-8") as file:
                json.dump(
                    {
                        "sourceLanguage": "en",
                        "strings": {
                            "title": {
                                "localizations": {
                                    "en": {"stringUnit": {"value": "Title"}}
                                }
                            },
                        },
                    },
                    file,
                )
            with open(source_path, "w", encoding="utf-8") as file:
                file.write("let title = L10n.title")

            result = subprocess.run(
                [
                    sys.executable,
                    "L10nXcstrings.py",
                    "--input",
                    xcstrings_path,
                    "--output-swift",
                    output_path,
                    "--output-unused",
                    unused_path,
                    "--source-dir",
                    temp_dir,
                ],
                cwd=os.getcwd(),
                capture_output=True,
                text=True,
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(os.path.exists(output_path))
            self.assertFalse(os.path.exists(unused_path))

    def test_generated_swift_typechecks_with_swift6_caller(self):
        swiftc = darwin_swiftc_or_skip(self)

        with tempfile.TemporaryDirectory() as temp_dir:
            xcstrings_path = os.path.join(temp_dir, "Localizable.xcstrings")
            output_path = os.path.join(temp_dir, "Generated.swift")
            caller_path = os.path.join(temp_dir, "Caller.swift")
            unused_path = os.path.join(temp_dir, "Unused.txt")
            data = {
                "sourceLanguage": "en",
                "strings": {
                    "class": {"localizations": {"en": {"stringUnit": {"value": "Class"}}}},
                    "count.value": {"localizations": {"en": {"stringUnit": {"value": "Count %d"}}}},
                    "escaped\"key": {"localizations": {"en": {"stringUnit": {"value": "Quote"}}}},
                    "initial": {"localizations": {"en": {"stringUnit": {"value": "Initial %c"}}}},
                    "name": {"localizations": {"en": {"stringUnit": {"value": "Name %@"}}}},
                    "pointer": {"localizations": {"en": {"stringUnit": {"value": "Pointer %p"}}}},
                    "progress": {
                        "localizations": {
                            "en": {"stringUnit": {"value": "Progress 100%% done"}}
                        }
                    },
                },
            }
            with open(xcstrings_path, "w", encoding="utf-8") as file:
                json.dump(data, file)

            args = MagicMock()
            args.input = xcstrings_path
            args.output_swift = output_path
            args.output_unused = unused_path
            args.source_dir = temp_dir
            args.enum_name = "L10n"
            args.ignore_dirs = []
            args.language = None
            args.allow_missing = False

            with contextlib.redirect_stdout(io.StringIO()):
                generate_strings(args)
            with open(caller_path, "w", encoding="utf-8") as file:
                file.write(
                    "\n".join(
                        [
                            "import Foundation",
                            "let title: String = L10n.`class`",
                            "let count: String = L10n.countValue(7)",
                            "let name: String = L10n.name(\"Serhiy\")",
                            "let pointer: String = L10n.pointer(1)",
                            "let progress: String = L10n.progress",
                        ]
                    )
                )

            run_checked(
                self,
                [swiftc, "-swift-version", "6", "-typecheck", output_path, caller_path],
            )

    def test_generated_swift_runs_with_bundle_strings_and_plurals(self):
        swiftc = darwin_swiftc_or_skip(self)

        with tempfile.TemporaryDirectory() as temp_dir:
            xcstrings_path = os.path.join(temp_dir, "Localizable.xcstrings")
            output_path = os.path.join(temp_dir, "Generated.swift")
            caller_path = os.path.join(temp_dir, "main.swift")
            runner_path = os.path.join(temp_dir, "Runner")
            unused_path = os.path.join(temp_dir, "Unused.txt")
            resources_path = os.path.join(temp_dir, "en.lproj")
            os.makedirs(resources_path)

            data = {
                "sourceLanguage": "en",
                "strings": {
                    "app.title": {
                        "localizations": {"en": {"stringUnit": {"value": "App Title"}}}
                    },
                    "files.count": {
                        "localizations": {
                            "en": {
                                "stringUnit": {"value": "%#@items@"},
                                "variations": {
                                    "plural": {
                                        "one": {"stringUnit": {"value": "%d file"}},
                                        "other": {"stringUnit": {"value": "%d files"}},
                                    }
                                },
                            }
                        }
                    },
                    "percent": {
                        "localizations": {
                            "en": {"stringUnit": {"value": "Progress 100%% done"}}
                        }
                    },
                    "welcome.name": {
                        "localizations": {"en": {"stringUnit": {"value": "Welcome, %@"}}}
                    },
                },
            }
            with open(xcstrings_path, "w", encoding="utf-8") as file:
                json.dump(data, file)

            with open(
                os.path.join(resources_path, "Localizable.strings"),
                "w",
                encoding="utf-8",
            ) as file:
                file.write(
                    textwrap.dedent(
                        r'''
                        "app.title" = "Runtime Title";
                        "percent" = "Progress 100%% done";
                        "welcome.name" = "Welcome, %@";
                        '''
                    ).strip()
                )
            with open(
                os.path.join(resources_path, "Localizable.stringsdict"),
                "w",
                encoding="utf-8",
            ) as file:
                file.write(
                    textwrap.dedent(
                        """\
                        <?xml version="1.0" encoding="UTF-8"?>
                        <!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
                          "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
                        <plist version="1.0">
                        <dict>
                          <key>files.count</key>
                          <dict>
                            <key>NSStringLocalizedFormatKey</key>
                            <string>%#@items@</string>
                            <key>items</key>
                            <dict>
                              <key>NSStringFormatSpecTypeKey</key>
                              <string>NSStringPluralRuleType</string>
                              <key>NSStringFormatValueTypeKey</key>
                              <string>d</string>
                              <key>one</key>
                              <string>%d file</string>
                              <key>other</key>
                              <string>%d files</string>
                            </dict>
                          </dict>
                        </dict>
                        </plist>
                        """
                    )
                )

            args = MagicMock()
            args.input = xcstrings_path
            args.output_swift = output_path
            args.output_unused = unused_path
            args.source_dir = temp_dir
            args.enum_name = "L10n"
            args.ignore_dirs = []
            args.language = None
            args.allow_missing = False

            with contextlib.redirect_stdout(io.StringIO()):
                generate_strings(args)
            with open(caller_path, "w", encoding="utf-8") as file:
                file.write(
                    "\n".join(
                        [
                            "import Foundation",
                            "print(L10n.appTitle)",
                            "print(L10n.filesCount(1))",
                            "print(L10n.filesCount(3))",
                            "print(L10n.percent)",
                            'print(L10n.welcomeName("Serhiy"))',
                        ]
                    )
                )

            run_checked(
                self,
                [swiftc, output_path, caller_path, "-o", runner_path],
            )
            result = run_checked(
                self,
                [runner_path],
                cwd=temp_dir,
            )

            self.assertEqual(
                result.stdout.splitlines(),
                [
                    "Runtime Title",
                    "1 file",
                    "3 files",
                    "Progress 100% done",
                    "Welcome, Serhiy",
                ],
            )


if __name__ == "__main__":
    unittest.main()
