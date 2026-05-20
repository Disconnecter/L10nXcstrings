from .identifiers import (
    SWIFT_IDENTIFIER_RE,
    SWIFT_KEYWORDS,
    SWIFT_NAME_RE,
    build_swiftified_keys,
    swift_case_name,
    swift_string_literal,
    swiftify_key,
    validate_swift_identifier,
)
from .swift_lexer import (
    parse_next_static_string_literal,
    parse_swift_static_string_literal,
    strip_swift_comments,
    strip_swift_comments_and_strings,
)
from .usage_scan import (
    DEFAULT_LOCALIZED_CALLS,
    DEFAULT_LOCALIZED_MEMBERS,
    find_native_localized_keys,
    find_shorthand_used_keys,
    find_used_keys_in_code,
    should_ignore_dir,
)

__all__ = [
    "DEFAULT_LOCALIZED_CALLS",
    "DEFAULT_LOCALIZED_MEMBERS",
    "SWIFT_IDENTIFIER_RE",
    "SWIFT_KEYWORDS",
    "SWIFT_NAME_RE",
    "build_swiftified_keys",
    "find_native_localized_keys",
    "find_shorthand_used_keys",
    "find_used_keys_in_code",
    "parse_next_static_string_literal",
    "parse_swift_static_string_literal",
    "sanitize_comment",
    "should_ignore_dir",
    "strip_swift_comments",
    "strip_swift_comments_and_strings",
    "swift_case_name",
    "swift_string_literal",
    "swiftify_key",
    "validate_swift_identifier",
]


def sanitize_comment(text):
    return " ".join(text.strip().splitlines())
