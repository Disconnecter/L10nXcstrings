def append_padding(result, text):
    result.extend("\n" if char == "\n" else " " for char in text)


def swift_string_prefix(content, idx):
    hash_count = 0
    while idx + hash_count < len(content) and content[idx + hash_count] == "#":
        hash_count += 1

    quote_idx = idx + hash_count
    if quote_idx >= len(content) or content[quote_idx] != '"':
        return None

    quote_count = 3 if content.startswith('"""', quote_idx) else 1
    return hash_count, quote_count


def strip_swift_line_comment(content, idx, result):
    append_padding(result, content[idx : idx + 2])
    idx += 2
    while idx < len(content) and content[idx] != "\n":
        result.append(" ")
        idx += 1
    return idx


def strip_swift_block_comment(content, idx, result):
    append_padding(result, content[idx : idx + 2])
    idx += 2
    depth = 1
    while idx < len(content) and depth:
        if content.startswith("/*", idx):
            append_padding(result, content[idx : idx + 2])
            idx += 2
            depth += 1
        elif content.startswith("*/", idx):
            append_padding(result, content[idx : idx + 2])
            idx += 2
            depth -= 1
        else:
            result.append("\n" if content[idx] == "\n" else " ")
            idx += 1
    return idx


def copy_swift_interpolation_expression(content, idx, result, hash_count):
    opener = "\\" + ("#" * hash_count) + "("
    append_padding(result, opener)
    idx += len(opener)
    depth = 1

    while idx < len(content) and depth:
        char = content[idx]
        next_char = content[idx + 1] if idx + 1 < len(content) else ""
        string_prefix = swift_string_prefix(content, idx)

        if char == "/" and next_char == "//":
            idx = strip_swift_line_comment(content, idx, result)
        elif char == "/" and next_char == "*":
            idx = strip_swift_block_comment(content, idx, result)
        elif string_prefix:
            idx = strip_swift_string_literal(content, idx, result, *string_prefix)
        elif char == "(":
            depth += 1
            result.append(char)
            idx += 1
        elif char == ")":
            depth -= 1
            result.append(char if depth else " ")
            idx += 1
        else:
            result.append(char)
            idx += 1

    return idx


def strip_swift_string_literal(content, idx, result, hash_count, quote_count):
    opener_length = hash_count + quote_count
    append_padding(result, content[idx : idx + opener_length])
    idx += opener_length
    close_delimiter = ('"' * quote_count) + ("#" * hash_count)
    interpolation_opener = "\\" + ("#" * hash_count) + "("

    while idx < len(content):
        if content.startswith(interpolation_opener, idx):
            idx = copy_swift_interpolation_expression(content, idx, result, hash_count)
            continue

        if content.startswith(close_delimiter, idx):
            append_padding(result, close_delimiter)
            idx += len(close_delimiter)
            break

        if hash_count == 0 and quote_count == 1 and content[idx] == "\\":
            escape = content[idx : idx + 2]
            append_padding(result, escape)
            idx += len(escape)
            continue

        result.append("\n" if content[idx] == "\n" else " ")
        idx += 1

    return idx


def skip_swift_string_literal(content, idx, hash_count, quote_count):
    idx += hash_count + quote_count
    close_delimiter = ('"' * quote_count) + ("#" * hash_count)
    interpolation_opener = "\\" + ("#" * hash_count) + "("

    while idx < len(content):
        if content.startswith(interpolation_opener, idx):
            idx += len(interpolation_opener)
            depth = 1
            while idx < len(content) and depth:
                char = content[idx]
                next_char = content[idx + 1] if idx + 1 < len(content) else ""
                nested_prefix = swift_string_prefix(content, idx)
                if char == "/" and next_char == "//":
                    idx += 2
                    while idx < len(content) and content[idx] != "\n":
                        idx += 1
                elif char == "/" and next_char == "*":
                    idx += 2
                    comment_depth = 1
                    while idx < len(content) and comment_depth:
                        if content.startswith("/*", idx):
                            idx += 2
                            comment_depth += 1
                        elif content.startswith("*/", idx):
                            idx += 2
                            comment_depth -= 1
                        else:
                            idx += 1
                elif nested_prefix:
                    idx = skip_swift_string_literal(content, idx, *nested_prefix)
                elif char == "(":
                    depth += 1
                    idx += 1
                elif char == ")":
                    depth -= 1
                    idx += 1
                else:
                    idx += 1
            continue

        if content.startswith(close_delimiter, idx):
            return idx + len(close_delimiter)

        if hash_count == 0 and quote_count == 1 and content[idx] == "\\":
            idx += 2
            continue

        idx += 1

    return idx


def strip_swift_comments_and_strings(content):
    result = []
    idx = 0
    while idx < len(content):
        char = content[idx]
        next_char = content[idx + 1] if idx + 1 < len(content) else ""
        string_prefix = swift_string_prefix(content, idx)

        if char == "/" and next_char == "/":
            idx = strip_swift_line_comment(content, idx, result)
            continue

        if char == "/" and next_char == "*":
            idx = strip_swift_block_comment(content, idx, result)
            continue

        if string_prefix:
            idx = strip_swift_string_literal(content, idx, result, *string_prefix)
            continue

        result.append(char)
        idx += 1
    return "".join(result)


def strip_swift_comments(content):
    result = []
    idx = 0
    while idx < len(content):
        char = content[idx]
        next_char = content[idx + 1] if idx + 1 < len(content) else ""
        string_prefix = swift_string_prefix(content, idx)

        if char == "/" and next_char == "/":
            idx = strip_swift_line_comment(content, idx, result)
            continue

        if char == "/" and next_char == "*":
            idx = strip_swift_block_comment(content, idx, result)
            continue

        if string_prefix:
            end = skip_swift_string_literal(content, idx, *string_prefix)
            result.append(content[idx:end])
            idx = end
            continue

        result.append(char)
        idx += 1
    return "".join(result)


def parse_next_static_string_literal(content, idx):
    while idx < len(content) and content[idx].isspace():
        idx += 1
    string_prefix = swift_string_prefix(content, idx)
    if not string_prefix:
        return None
    return parse_swift_static_string_literal(content, idx, *string_prefix)


def parse_swift_static_string_literal(content, idx, hash_count, quote_count):
    idx += hash_count + quote_count
    close_delimiter = ('"' * quote_count) + ("#" * hash_count)
    interpolation_opener = "\\" + ("#" * hash_count) + "("
    value = []

    while idx < len(content):
        if content.startswith(interpolation_opener, idx):
            return None
        if content.startswith(close_delimiter, idx):
            return "".join(value), idx + len(close_delimiter)
        if hash_count == 0 and content[idx] == "\\":
            if idx + 1 >= len(content):
                return None
            escape = content[idx + 1]
            escapes = {
                "\\": "\\",
                '"': '"',
                "n": "\n",
                "r": "\r",
                "t": "\t",
            }
            value.append(escapes.get(escape, escape))
            idx += 2
            continue
        value.append(content[idx])
        idx += 1

    return None
