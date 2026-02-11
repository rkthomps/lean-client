from lean_client.lsp_utils import parse_lean_docstring


def test_parse_lean_docstring() -> None:
    docstring = "/--\nThis is a docstring\n-/"
    assert parse_lean_docstring(docstring) == docstring

    docstring_with_whitespace = (
        "   \n  \n/--\nThis is a docstring with leading whitespace\n-/"
    )
    assert parse_lean_docstring(
        docstring_with_whitespace) == docstring_with_whitespace

    docstring_with_trailing_whitespace = (
        "   \n  \n/--\nThis is a docstring with leading whitespace\n-/\n   \n  \n"
    )
    assert parse_lean_docstring(
        docstring_with_trailing_whitespace) == docstring_with_trailing_whitespace

    nested_docstring = "/--\nThis is a docstring with a nested docstring\n/--\nNested docstring\n-/\n-/"
    other_stuff = "This is other stuff after the docstring"
    assert parse_lean_docstring(
        nested_docstring + other_stuff) == nested_docstring

    no_docstring = "theorem test : True := by trivial"
    assert parse_lean_docstring(no_docstring) is None

    unclosed_docstring = "/--\nThis is an unclosed docstring"
    assert parse_lean_docstring(unclosed_docstring) is None
