import os
import re

from .identifiers import SWIFT_NAME_RE
from .swift_lexer import (
    parse_next_static_string_literal,
    strip_swift_comments,
    strip_swift_comments_and_strings,
)

DEFAULT_LOCALIZED_CALLS = (
    "NSLocalizedString",
    "Text",
    "Button",
    "Label",
    "Toggle",
    "Picker",
    "Section",
    "NavigationLink",
    "Menu",
    "Link",
    "LocalizedStringResource",
)
DEFAULT_LOCALIZED_MEMBERS = (
    "navigationTitle",
    "navigationSubtitle",
    "alert",
    "confirmationDialog",
)


def should_ignore_dir(root, dir_name, source_dir, ignore_dirs):
    dir_path = os.path.join(root, dir_name)
    rel_path = os.path.relpath(dir_path, source_dir)
    rel_norm = os.path.normpath(rel_path)
    rel_parts = rel_norm.split(os.sep)
    for ignore in ignore_dirs:
        ignore_norm = os.path.normpath(ignore)
        if os.sep in ignore_norm:
            if rel_norm == ignore_norm or rel_norm.startswith(ignore_norm + os.sep):
                return True
        elif ignore_norm in rel_parts:
            return True
    return False


def find_used_keys_in_code(
    source_dir,
    keys,
    enum_name,
    ignore_dirs,
    original_key_to_swift=None,
    localized_calls=None,
    localized_members=None,
):
    used_keys = set()
    known_keys = set(keys)
    original_key_to_swift = original_key_to_swift or {}
    localized_calls = merge_localized_names(DEFAULT_LOCALIZED_CALLS, localized_calls)
    localized_members = merge_localized_names(DEFAULT_LOCALIZED_MEMBERS, localized_members)
    explicit_pattern = re.compile(
        rf"\b{re.escape(enum_name)}\."
        rf"(?:`({SWIFT_NAME_RE})`|({SWIFT_NAME_RE})\b)"
    )
    shorthand_pattern = re.compile(rf"\.(?:`({SWIFT_NAME_RE})`|({SWIFT_NAME_RE})\b)")

    for root, dirs, files in os.walk(source_dir):
        dirs[:] = [
            d for d in dirs if not should_ignore_dir(root, d, source_dir, ignore_dirs)
        ]
        for file in files:
            if not file.endswith(".swift"):
                continue
            with open(os.path.join(root, file), encoding="utf-8") as swift_file:
                raw_content = swift_file.read()
            used_keys.update(
                find_native_localized_keys(
                    strip_swift_comments(raw_content),
                    known_keys,
                    original_key_to_swift,
                    localized_calls,
                    localized_members,
                )
            )
            content = strip_swift_comments_and_strings(raw_content)
            used_keys.update(
                match
                for match in (
                    match.group(1) or match.group(2)
                    for match in explicit_pattern.finditer(content)
                )
                if match in known_keys
            )
            used_keys.update(
                find_shorthand_used_keys(content, known_keys, enum_name, shorthand_pattern)
            )

    return used_keys


def find_native_localized_keys(
    content,
    known_keys,
    original_key_to_swift,
    localized_calls=None,
    localized_members=None,
):
    used = set()
    for start_idx in localized_string_argument_starts(
        content,
        localized_calls or DEFAULT_LOCALIZED_CALLS,
        localized_members or DEFAULT_LOCALIZED_MEMBERS,
    ):
        parsed = parse_next_static_string_literal(content, start_idx)
        if not parsed:
            continue
        value, _ = parsed
        if value in original_key_to_swift:
            used.add(original_key_to_swift[value])
        elif value in known_keys:
            used.add(value)
    return used


def merge_localized_names(defaults, extra):
    names = list(defaults)
    for name in extra or ():
        if name not in names:
            names.append(name)
    return tuple(names)


def localized_string_argument_starts(content, localized_calls, localized_members):
    yield from call_argument_starts(content, localized_calls)
    yield from member_argument_starts(content, localized_members)
    yield from string_localized_argument_starts(content)


def call_argument_starts(content, localized_calls):
    if not localized_calls:
        return
    names = "|".join(re.escape(name) for name in localized_calls)
    pattern = re.compile(rf"\b(?:{names})\s*\(")
    for match in pattern.finditer(content):
        yield match.end()


def member_argument_starts(content, localized_members):
    if not localized_members:
        return
    names = "|".join(re.escape(name) for name in localized_members)
    pattern = re.compile(rf"\.(?:{names})\s*\(")
    for match in pattern.finditer(content):
        yield match.end()


def string_localized_argument_starts(content):
    pattern = re.compile(r"\bString\s*\(\s*localized\s*:")
    for match in pattern.finditer(content):
        yield match.end()


def find_shorthand_used_keys(content, known_keys, enum_name, shorthand_pattern):
    enum_values = set(find_typed_value_names(content, enum_name))
    used = set()
    lines = content.splitlines()

    for line in lines:
        if re.search(rf":\s*{re.escape(enum_name)}\b", line):
            used.update(shorthand_matches(line, known_keys, shorthand_pattern))

    for value_name in enum_values:
        for switch_body in switch_bodies_for_value(content, value_name):
            for case_clause in top_level_switch_case_clauses(switch_body):
                used.update(shorthand_matches(case_clause, known_keys, shorthand_pattern))

    return used


def find_typed_value_names(content, enum_name):
    escaped_enum = re.escape(enum_name)
    typed_name_pattern = re.compile(rf"\b({SWIFT_NAME_RE})\s*:\s*{escaped_enum}\b")
    return {match.group(1) for match in typed_name_pattern.finditer(content)}


def switch_bodies_for_value(content, value_name):
    switch_pattern = re.compile(rf"\bswitch\s+{re.escape(value_name)}\s*\{{")
    for match in switch_pattern.finditer(content):
        body = balanced_brace_body(content, match.end() - 1)
        if body is not None:
            yield body


def balanced_brace_body(content, open_brace_idx):
    depth = 0
    for idx in range(open_brace_idx, len(content)):
        char = content[idx]
        if char == "{":
            depth += 1
        elif char == "}":
            depth -= 1
            if depth == 0:
                return content[open_brace_idx + 1 : idx]
    return None


def top_level_switch_case_clauses(content):
    idx = 0
    depth = 0
    while idx < len(content):
        char = content[idx]
        if char in "{([":
            depth += 1
            idx += 1
            continue
        if char in "})]":
            depth = max(0, depth - 1)
            idx += 1
            continue
        if depth == 0 and is_case_keyword_at(content, idx):
            end = top_level_clause_end(content, idx + len("case"))
            yield content[idx:end]
            idx = end
            continue
        idx += 1


def is_case_keyword_at(content, idx):
    if not content.startswith("case", idx):
        return False
    before = content[idx - 1] if idx > 0 else " "
    after_idx = idx + len("case")
    after = content[after_idx] if after_idx < len(content) else " "
    return not (before.isalnum() or before == "_") and not (
        after.isalnum() or after == "_"
    )


def top_level_clause_end(content, idx):
    depth = 0
    while idx < len(content):
        char = content[idx]
        if char in "{([":
            depth += 1
        elif char in "})]":
            depth = max(0, depth - 1)
        elif char == ":" and depth == 0:
            return idx
        idx += 1
    return idx


def shorthand_matches(content, known_keys, shorthand_pattern):
    return {
        match
        for match in (
            match.group(1) or match.group(2)
            for match in shorthand_pattern.finditer(content)
        )
        if match in known_keys
    }
