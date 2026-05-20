from .cli import generate_strings, main, parse_args
from .codegen import build_generated_swift, build_placeholder_metadata, find_unused_keys
from .format import extract_placeholder_types
from .swift import (
    SWIFT_IDENTIFIER_RE,
    SWIFT_KEYWORDS,
    build_swiftified_keys,
    find_used_keys_in_code,
    sanitize_comment,
    strip_swift_comments_and_strings,
    swift_case_name,
    swift_string_literal,
    swiftify_key,
    validate_swift_identifier,
)
from .xcstrings import (
    LocalizedString,
    collect_string_unit_values,
    get_keys_and_strings_from_xcstrings,
    get_localized_strings_from_xcstrings,
)

__all__ = [
    "LocalizedString",
    "SWIFT_IDENTIFIER_RE",
    "SWIFT_KEYWORDS",
    "build_generated_swift",
    "build_placeholder_metadata",
    "build_swiftified_keys",
    "collect_string_unit_values",
    "extract_placeholder_types",
    "find_unused_keys",
    "find_used_keys_in_code",
    "generate_strings",
    "get_keys_and_strings_from_xcstrings",
    "get_localized_strings_from_xcstrings",
    "main",
    "parse_args",
    "sanitize_comment",
    "strip_swift_comments_and_strings",
    "swift_case_name",
    "swift_string_literal",
    "swiftify_key",
    "validate_swift_identifier",
]
