import json
import sys
from dataclasses import dataclass


@dataclass(frozen=True)
class LocalizedString:
    display_value: str
    values: tuple[str, ...]


def collect_string_unit_values(node):
    values = []
    if isinstance(node, dict):
        string_unit = node.get("stringUnit")
        if isinstance(string_unit, dict) and "value" in string_unit:
            values.append(string_unit["value"])
        for value in node.values():
            values.extend(collect_string_unit_values(value))
    elif isinstance(node, list):
        for item in node:
            values.extend(collect_string_unit_values(item))
    return values


def get_localized_strings_from_xcstrings(path, language=None, allow_missing=False):
    with open(path, encoding="utf-8") as file:
        data = json.load(file)

    selected_language = language or data.get("sourceLanguage") or "en"
    result = {}
    missing = []
    strings = data.get("strings", {})
    for key, val in strings.items():
        localization = val.get("localizations", {}).get(selected_language)
        if not localization:
            missing.append(f"{key}: missing {selected_language!r} localization")
            continue

        values = tuple(collect_string_unit_values(localization))
        if not values:
            missing.append(
                f"{key}: missing stringUnit.value for {selected_language!r}"
            )
            continue

        result[key] = LocalizedString(display_value=values[0], values=values)

    if missing and not allow_missing:
        details = "\n".join(f" - {item}" for item in missing)
        raise ValueError(f"Missing localizations in {path}:\n{details}")

    for item in missing:
        print(f"Skipping {item}", file=sys.stderr)

    return result


def get_keys_and_strings_from_xcstrings(path, language=None, allow_missing=False):
    localized_strings = get_localized_strings_from_xcstrings(
        path,
        language,
        allow_missing,
    )
    return {
        key: localized_string.display_value
        for key, localized_string in localized_strings.items()
    }
