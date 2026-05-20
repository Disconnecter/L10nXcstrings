import argparse
import os
import sys

from .codegen import build_generated_swift, build_generation_context
from .xcstrings import get_localized_strings_from_xcstrings


def generate_strings(args):
    keys_and_strings = get_localized_strings_from_xcstrings(
        args.input,
        getattr(args, "language", None),
        getattr(args, "allow_missing", False),
    )
    swiftified_keys, placeholder_metadata, unused_keys = build_generation_context(
        args,
        keys_and_strings,
    )
    generated = build_generated_swift(
        args,
        keys_and_strings,
        swiftified_keys,
        placeholder_metadata,
        unused_keys,
    )

    output_dir = os.path.dirname(args.output_swift)
    if output_dir:
        os.makedirs(output_dir, exist_ok=True)

    with open(args.output_swift, "w", encoding="utf-8") as file:
        file.write(generated)

    print(f"Generated {args.output_swift} with {len(keys_and_strings)} keys.")
    return generated


def parse_args(argv=None):
    parser = argparse.ArgumentParser(
        description="Generate Swift localization helpers and check unused keys."
    )
    parser.add_argument(
        "--input",
        default="Localizable.xcstrings",
        help="Path to .xcstrings file",
    )
    parser.add_argument(
        "--output-swift",
        default="Generated/Strings+Generated.swift",
        help="Path to output .swift file",
    )
    parser.add_argument(
        "--output-unused",
        default="Unused.txt",
        help="File to write unused keys to",
    )
    parser.add_argument(
        "--source-dir",
        default=".",
        help="Directory to scan Swift source code",
    )
    parser.add_argument(
        "--ignore-dirs",
        nargs="+",
        default=[],
        help="Directories to ignore during scanning. Space-separated.",
    )
    parser.add_argument(
        "--enum-name",
        default="L10n",
        help="Name of the generated Swift namespace enum",
    )
    parser.add_argument(
        "--language",
        default=None,
        help="Localization language to read. Defaults to sourceLanguage or en",
    )
    parser.add_argument(
        "--allow-missing",
        action="store_true",
        help="Skip keys missing the selected localization instead of failing",
    )
    parser.add_argument(
        "--table-name",
        default=None,
        help="Localization table name to pass to NSLocalizedString",
    )
    parser.add_argument(
        "--bundle",
        default="Bundle.main",
        help="Swift bundle expression to pass to NSLocalizedString",
    )
    parser.add_argument(
        "--localized-call",
        dest="localized_calls",
        action="append",
        default=None,
        help=(
            "Additional Swift function/type call whose first string literal "
            "argument should count as a localization key. Can be repeated."
        ),
    )
    parser.add_argument(
        "--localized-member",
        dest="localized_members",
        action="append",
        default=None,
        help=(
            "Additional Swift member call whose first string literal argument "
            "should count as a localization key. Can be repeated."
        ),
    )
    return parser.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)
    try:
        generate_strings(args)
    except (OSError, ValueError) as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
    return 0
