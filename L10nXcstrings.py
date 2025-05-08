#!/usr/bin/env python3

import json
import os
import re
import argparse

def get_keys_and_strings_from_xcstrings(path):
    with open(path, "r", encoding="utf-8") as file:
        data = json.load(file)

    result = {}
    strings = data.get("strings", {})
    for key, val in strings.items():
        try:
            string_val = val["localizations"]["en"]["stringUnit"]["value"]
            result[key] = string_val
        except KeyError:
            pass
    return result

def extract_placeholder_types(string_value: str) -> list[str]:
    pattern = r'%(\d+\$)?[+\-#0 ]*(?:\d+)?(?:\.\d+)?[hlL]?([@diufFeEgGxXoscp])'
    matches = list(re.finditer(pattern, string_value))

    positionals = {}
    order = []

    def swift_type(spec):
        if spec in {'d', 'i'}:
            return 'Int'
        elif spec in {'u'}:
            return 'UInt'
        elif spec in {'f', 'F', 'e', 'E', 'g', 'G'}:
            return 'Double'
        elif spec in {'@'}:
            return 'String'
        elif spec in {'c'}:
            return 'Character'
        elif spec in {'li', 'ld'}:
            return 'Int64'
        else:
            return 'CVarArg'

    for idx, match in enumerate(matches):
        pos, spec = match.groups()
        typ = swift_type(spec)

        if pos:
            index = int(pos[:-1]) - 1
            positionals[index] = typ
        else:
            order.append(typ)

    if positionals:
        return [positionals[i] for i in sorted(positionals.keys())]
    else:
        return order

def swiftify_key(key: str) -> str:
    return re.sub(r'[._-](\w)', lambda m: m.group(1).upper(), key)

def find_used_keys_in_code(source_dir, keys, enum_name):
    used_keys = set()
    pattern = re.compile(rf'\b{re.escape(enum_name)}\.([a-zA-Z0-9_]+)\b')

    for root, _, files in os.walk(source_dir):
        for file in files:
            if file.endswith(".swift"):
                with open(os.path.join(root, file), "r", encoding="utf-8") as f:
                    content = f.read()
                    matches = pattern.findall(content)
                    used_keys.update(matches)

    return used_keys

def find_unused_keys(args, swiftified_keys):
    defined_keys = set(swiftified_keys.keys())
    used_keys = find_used_keys_in_code(args.source_dir, defined_keys, args.enum_name)
    unused = defined_keys - used_keys

    if os.path.exists(args.output_unused):
        os.remove(args.output_unused)

    if unused:
        print("Unused Keys:")
        with open(args.output_unused, "w", encoding="utf-8") as f:
            for key in sorted(unused):
                print(f" - {key}")
                f.write(f"{swiftified_keys[key]}\n")

        print(f"\nTotal: {len(unused)} unused of {len(defined_keys)} keys.")
    return unused

def sanitize_comment(text):
        return ' '.join(text.strip().splitlines())

def generate_strings(args):
    keys_and_strings = get_keys_and_strings_from_xcstrings(args.input)
    sorted_keys = sorted(keys_and_strings.keys())

    swiftified_keys = {swiftify_key(k): k for k in sorted_keys}
    unused_keys = find_unused_keys(args, swiftified_keys)

    os.makedirs(os.path.dirname(args.output_swift), exist_ok=True)

    with open(args.output_swift, "w", encoding="utf-8") as f:
        f.write("// swiftlint:disable all\n")
        f.write(f"// Generated from {os.path.basename(args.input)}\n")
        f.write(f"// Do not edit manually\n\n")
        f.write("import Foundation\n\n")
        f.write(f"public enum {args.enum_name}: Equatable, Hashable {{\n")

        for key in sorted_keys:
            swift_key = swiftify_key(key)
            string_value = keys_and_strings[key]
            types = extract_placeholder_types(string_value)
            comment = f"  /// {sanitize_comment(string_value)}"
            if swift_key in unused_keys:
                comment = f"  #warning(\"Unused key: {swift_key}\")\n" + comment
            f.write(f"{comment}\n")
            if types:
                f.write(f"  case {swift_key}({', '.join(types)})\n")
            else:
                f.write(f"  case {swift_key}\n")

        f.write("}\n\n")

        f.write(f"extension {args.enum_name}: CustomStringConvertible {{\n")
        f.write("  public var description: String { return self.string }\n\n")
        f.write("  public var string: String {\n")
        f.write("    switch self {\n")

        for key in sorted_keys:
            swift_key = swiftify_key(key)
            types = extract_placeholder_types(keys_and_strings[key])
            if types:
                params = [f"p{i+1}" for i in range(len(types))]
                pattern = ", ".join(f"let {p}" for p in params)
                call_args = ", ".join(params)
                f.write(f"    case .{swift_key}({pattern}):\n")
                f.write(f'      return {args.enum_name}.tr(key: "{key}", {call_args})\n')
            else:
                f.write(f"    case .{swift_key}:\n")
                f.write(f'      return {args.enum_name}.tr(key: "{key}")\n')

        f.write("    }\n  }\n\n")

        f.write("  private static func tr(key: String, _ args: CVarArg...) -> String {\n")
        f.write("    let format = NSLocalizedString(key, comment: key)\n")
        f.write("    return String(format: format, arguments: args)\n")
        f.write("  }\n")
        f.write("}\n")

    print(f"Generated {args.output_swift} with {len(sorted_keys)} keys.")

def parse_args():
    parser = argparse.ArgumentParser(description="Generate Swift localization enum and check unused keys.")
    parser.add_argument("--input", default="Localizable.xcstrings", help="Path to .xcstrings file")
    parser.add_argument("--output-swift", default="Generated/Strings+Generated.swift", help="Path to output .swift file")
    parser.add_argument("--output-unused", default="Unused.txt", help="File to write unused keys to")
    parser.add_argument("--source-dir", default=".", help="Directory to scan Swift source code")
    parser.add_argument("--enum-name", default="L10n", help="Name of the generated enum")
    return parser.parse_args()

def main():
    args = parse_args()
    generate_strings(args)

if __name__ == "__main__":
    main()
