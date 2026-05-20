import re

FORMAT_SPECIFIERS = "@diufFeEgGxXocp"
LENGTH_MODIFIERS = ("hh", "ll", "h", "l", "L", "z", "t", "j")


def extract_placeholder_types(string_value: str) -> list[str]:
    def swift_type(length, spec):
        if spec in {"d", "i"}:
            if length == "ll":
                return "Int64"
            return "Int"
        if spec in {"u", "o", "x", "X", "p"}:
            if length == "ll":
                return "UInt64"
            return "UInt"
        if spec in {"f", "F", "e", "E", "g", "G"}:
            return "Double"
        if spec == "@":
            return "String"
        if spec == "c":
            return "Int"
        raise ValueError(f"Unsupported format specifier: %{spec}")

    placeholders = []
    idx = 0
    while idx < len(string_value):
        if string_value[idx] != "%":
            idx += 1
            continue
        if idx + 1 < len(string_value) and string_value[idx + 1] == "%":
            idx += 2
            continue

        cursor = idx + 1
        position = None
        positional_match = re.match(r"(\d+)\$", string_value[cursor:])
        if positional_match:
            position_number = int(positional_match.group(1))
            if position_number < 1:
                raise ValueError("Positional placeholders are 1-based")
            position = position_number - 1
            cursor += len(positional_match.group(0))

        plural_match = re.match(r"#@[^@]+@", string_value[cursor:])
        if plural_match:
            placeholders.append((position, "CVarArg"))
            idx = cursor + len(plural_match.group(0))
            continue

        while cursor < len(string_value) and string_value[cursor] in "+-#0 ":
            cursor += 1

        width_match = re.match(r"\d+", string_value[cursor:])
        if width_match:
            cursor += len(width_match.group(0))
        elif cursor < len(string_value) and string_value[cursor] == "*":
            raise ValueError("Dynamic printf widths are not supported")

        if cursor < len(string_value) and string_value[cursor] == ".":
            cursor += 1
            precision_match = re.match(r"\d+", string_value[cursor:])
            if precision_match:
                cursor += len(precision_match.group(0))
            elif cursor < len(string_value) and string_value[cursor] == "*":
                raise ValueError("Dynamic printf precisions are not supported")

        length = None
        for modifier in LENGTH_MODIFIERS:
            if string_value.startswith(modifier, cursor):
                length = modifier
                cursor += len(modifier)
                break

        if cursor >= len(string_value):
            raise ValueError(f"Incomplete format placeholder in {string_value!r}")

        spec = string_value[cursor]
        if spec == "s":
            raise ValueError("C string placeholder %s is not supported; use %@ for Swift strings")
        if spec not in FORMAT_SPECIFIERS:
            raise ValueError(f"Unsupported format specifier: %{spec}")
        if spec == "c" and cursor + 1 < len(string_value) and (
            string_value[cursor + 1].isalnum() or string_value[cursor + 1] == "_"
        ):
            raise ValueError(
                "Ambiguous %c placeholder next to alphanumeric text; "
                "escape literal percent signs as %%"
            )
        placeholders.append((position, swift_type(length, spec)))
        idx = cursor + 1

    if not placeholders:
        return []

    has_positionals = any(position is not None for position, _ in placeholders)
    if has_positionals:
        if any(position is None for position, _ in placeholders):
            raise ValueError(
                "Mixed positional and non-positional placeholders are not supported"
            )

        positionals = {}
        for position, typ in placeholders:
            if position in positionals and positionals[position] != typ:
                raise ValueError(
                    f"Conflicting types for positional placeholder %{position + 1}$"
                )
            positionals[position] = typ
        max_index = max(positionals.keys(), default=-1)
        missing = [
            index + 1 for index in range(max_index + 1) if index not in positionals
        ]
        if missing:
            raise ValueError(f"Missing positional placeholders: {missing}")
        return [positionals[index] for index in range(max_index + 1)]

    return [typ for _, typ in placeholders]
