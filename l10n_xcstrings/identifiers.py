import hashlib
import re

SWIFT_KEYWORDS = {
    "Any",
    "Protocol",
    "Self",
    "Type",
    "actor",
    "as",
    "associatedtype",
    "async",
    "await",
    "break",
    "case",
    "catch",
    "class",
    "continue",
    "default",
    "defer",
    "deinit",
    "do",
    "else",
    "enum",
    "extension",
    "fallthrough",
    "false",
    "fileprivate",
    "for",
    "func",
    "guard",
    "if",
    "import",
    "in",
    "indirect",
    "init",
    "inout",
    "internal",
    "is",
    "let",
    "nil",
    "nonisolated",
    "open",
    "operator",
    "private",
    "precedencegroup",
    "protocol",
    "public",
    "rethrows",
    "return",
    "self",
    "some",
    "static",
    "struct",
    "subscript",
    "super",
    "switch",
    "throw",
    "throws",
    "true",
    "try",
    "typealias",
    "var",
    "where",
    "while",
}

SWIFT_IDENTIFIER_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
SWIFT_NAME_RE = r"[A-Za-z_][A-Za-z0-9_]*"


def swiftify_key(key: str) -> str:
    parts = re.findall(r"[A-Za-z0-9]+", key)
    if not parts:
        return "key" + stable_key_hash(key)

    identifier = parts[0] + "".join(part[:1].upper() + part[1:] for part in parts[1:])
    if identifier[0].isdigit():
        identifier = "_" + identifier
    if any(ord(char) > 127 for char in key):
        identifier += stable_key_hash(key)
    return identifier


def stable_key_hash(key: str) -> str:
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:8]
    return digest[:1].upper() + digest[1:]


def swift_case_name(identifier: str) -> str:
    if identifier in SWIFT_KEYWORDS:
        return f"`{identifier}`"
    return identifier


def validate_swift_identifier(identifier: str, label: str, allow_keyword=False):
    if not SWIFT_IDENTIFIER_RE.match(identifier):
        raise ValueError(f"{label} is not a valid Swift identifier: {identifier!r}")
    if not allow_keyword and identifier in SWIFT_KEYWORDS:
        raise ValueError(f"{label} is a reserved Swift keyword: {identifier!r}")


def build_swiftified_keys(sorted_keys):
    swiftified_keys = {}
    collisions = {}
    for key in sorted_keys:
        identifier = swiftify_key(key)
        validate_swift_identifier(identifier, f"Localization key {key!r}", allow_keyword=True)
        existing = swiftified_keys.get(identifier)
        if existing:
            collisions.setdefault(identifier, [existing]).append(key)
        else:
            swiftified_keys[identifier] = key

    if collisions:
        details = ", ".join(
            f"{identifier}: {', '.join(keys)}"
            for identifier, keys in sorted(collisions.items())
        )
        raise ValueError(f"Swift key collisions detected: {details}")
    return swiftified_keys


def swift_string_literal(value: str) -> str:
    escaped = []
    for char in value:
        if char == "\\":
            escaped.append("\\\\")
        elif char == '"':
            escaped.append('\\"')
        elif char == "\n":
            escaped.append("\\n")
        elif char == "\r":
            escaped.append("\\r")
        elif char == "\t":
            escaped.append("\\t")
        elif ord(char) < 32:
            escaped.append(f"\\u{{{ord(char):x}}}")
        else:
            escaped.append(char)
    return '"' + "".join(escaped) + '"'
