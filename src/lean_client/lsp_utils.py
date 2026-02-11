from dataclasses import dataclass
from typing import Optional
from lean_client.client import Range, Position


def get_range_str(content: str, r: Range) -> str:
    lines = content.split("\n")
    line_slice = lines[r.start.line: r.end.line + 1].copy()
    line_slice[-1] = line_slice[-1][: r.end.character]
    line_slice[0] = line_slice[0][r.start.character:]
    return "\n".join(line_slice)


def str_to_pos(s: str) -> Position:
    """
    Given a string, this function returns the ending position of the string.
    The ending position is one past the last character of the string.
    """
    s_lines = s.split("\n")
    if len(s_lines) == 0:
        return Position(line=0, character=0)
    end_char = len(s_lines[-1])
    end_line = len(s_lines) - 1
    return Position(line=end_line, character=end_char)


@dataclass
class ParseResult:
    parsed: str
    rest: str


def consume_whitespace(s: str) -> ParseResult:
    stripped_string = s.lstrip()
    stripped_space = s[: len(s) - len(stripped_string)]
    return ParseResult(parsed=stripped_space, rest=stripped_string)


def parse_lean_docstring(s: str) -> Optional[str]:
    """
    Parses lean docstring (i.e. /-- docstring -/)
    Consumes leading and trailing whitespace
    """
    whitespace = consume_whitespace(s)
    if not whitespace.rest.startswith("/--"):
        return None
    rest = whitespace.rest[3:]
    num_closing_dashes = 0
    for i in range(len(rest)):
        if rest[i: i + 2] == "/-":
            num_closing_dashes += 1
        elif rest[i: i + 2] == "-/":
            if num_closing_dashes == 0:
                doc_str = whitespace.parsed + \
                    whitespace.rest[:3] + rest[: i + 2]
                trailing_whitespace = consume_whitespace(rest[i + 2:])
                doc_str += trailing_whitespace.parsed
                assert s.startswith(doc_str)
                return doc_str
            else:
                num_closing_dashes -= 1
    return None
