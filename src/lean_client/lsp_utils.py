from lean_client.client import Range


def get_range_str(content: str, r: Range) -> str:
    lines = content.split("\n")
    line_slice = lines[r.start.line : r.end.line + 1].copy()
    line_slice[-1] = line_slice[-1][: r.end.character]
    line_slice[0] = line_slice[0][r.start.character :]
    return "\n".join(line_slice)
