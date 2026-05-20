import os

from .format import extract_placeholder_types
from .swift import (
    build_swiftified_keys,
    find_used_keys_in_code,
    sanitize_comment,
    swift_case_name,
    swift_string_literal,
    swiftify_key,
    validate_swift_identifier,
)


def localized_display_value(value):
    return getattr(value, "display_value", value)


def localized_value_variants(value):
    return getattr(value, "values", (value,))


def merge_placeholder_types(key, variants):
    extracted = []
    for variant in variants:
        try:
            extracted.append(extract_placeholder_types(variant))
        except ValueError as error:
            raise ValueError(f"{key!r}: {error}") from error

    non_empty = [types for types in extracted if types]
    if not non_empty:
        return []

    merged = non_empty[0]
    for types in non_empty[1:]:
        merged = merge_compatible_type_lists(merged, types)
        if merged is None:
            break
    if merged is None:
        raise ValueError(
            f"{key!r}: inconsistent placeholder types across variations: "
            f"{non_empty}"
        )
    return merged


def merge_compatible_type_lists(left, right):
    if len(left) != len(right):
        return None
    merged = []
    for left_type, right_type in zip(left, right):
        if left_type == right_type:
            merged.append(left_type)
        elif left_type == "CVarArg":
            merged.append(right_type)
        elif right_type == "CVarArg":
            merged.append(left_type)
        else:
            return None
    return merged


def build_placeholder_metadata(sorted_keys, keys_and_strings):
    metadata = {}
    for key in sorted_keys:
        metadata[key] = merge_placeholder_types(
            key,
            localized_value_variants(keys_and_strings[key]),
        )
    return metadata


def find_unused_keys(args, swiftified_keys):
    defined_keys = set(swiftified_keys.keys())
    used_keys = find_used_keys_in_code(
        args.source_dir,
        defined_keys,
        args.enum_name,
        args.ignore_dirs,
        {original: swift for swift, original in swiftified_keys.items()},
        getattr(args, "localized_calls", None),
        getattr(args, "localized_members", None),
    )
    unused = defined_keys - used_keys

    if os.path.exists(args.output_unused):
        os.remove(args.output_unused)

    if unused:
        print("Unused Keys:")
        with open(args.output_unused, "w", encoding="utf-8") as file:
            for key in sorted(unused):
                print(f" - {key}")
                file.write(f"{swiftified_keys[key]}\n")

        print(f"\nTotal: {len(unused)} unused of {len(defined_keys)} keys.")
    return unused


def build_generated_swift(
    args,
    keys_and_strings,
    swiftified_keys,
    placeholder_metadata,
    unused_keys,
):
    sorted_keys = sorted(keys_and_strings.keys())
    table_name = optional_string_arg(args, "table_name")
    bundle = string_arg(args, "bundle", "Bundle.main")
    lines = [
        "// swiftlint:disable all",
        f"// Generated from {os.path.basename(args.input)}",
        "// Do not edit manually",
        "",
        "import Foundation",
        "",
        f"public enum {args.enum_name} {{",
    ]

    for key in sorted_keys:
        swift_key = swiftify_key(key)
        swift_case = swift_case_name(swift_key)
        string_value = localized_display_value(keys_and_strings[key])
        types = placeholder_metadata[key]
        if swift_key in unused_keys:
            lines.append(f'  #warning("Unused key: {swift_key}")')
        lines.append(f"  /// {sanitize_comment(string_value)}")
        if types:
            params = ", ".join(
                f"_ p{index}: {typ}" for index, typ in enumerate(types, start=1)
            )
            call_args = ", ".join(f"p{index}" for index in range(1, len(types) + 1))
            lines.append(
                f"  public static func {swift_case}({params}) -> String {{"
            )
            lines.append(
                f"    return tr(key: {swift_string_literal(key)}, {call_args})"
            )
            lines.append("  }")
        else:
            lines.append(f"  public static var {swift_case}: String {{")
            lines.append(f"    return tr(key: {swift_string_literal(key)})")
            lines.append("  }")
        lines.append("")

    lines.extend(
        [
            "  private static func tr(key: String, _ args: CVarArg...) -> String {",
            "    let format = NSLocalizedString(",
            "      key,",
            f"      tableName: {swift_optional_string_literal(table_name)},",
            f"      bundle: {bundle},",
            '      value: "",',
            "      comment: key",
            "    )",
            "    return String.localizedStringWithFormat(format, args)",
            "  }",
            "}",
            "",
        ]
    )
    return "\n".join(lines)


def swift_optional_string_literal(value):
    if value is None:
        return "nil"
    return swift_string_literal(value)


def optional_string_arg(args, name):
    value = getattr(args, name, None)
    if isinstance(value, str) and value:
        return value
    return None


def string_arg(args, name, default):
    value = getattr(args, name, default)
    if isinstance(value, str) and value:
        return value
    return default


def build_generation_context(args, keys_and_strings):
    sorted_keys = sorted(keys_and_strings.keys())
    validate_swift_identifier(args.enum_name, "Enum name")
    swiftified_keys = build_swiftified_keys(sorted_keys)
    placeholder_metadata = build_placeholder_metadata(sorted_keys, keys_and_strings)
    unused_keys = find_unused_keys(args, swiftified_keys)
    return swiftified_keys, placeholder_metadata, unused_keys
