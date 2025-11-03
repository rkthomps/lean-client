from dataclasses import dataclass
from pathlib import Path
import textwrap
from typing import Any

from lean_client.client import (
    LeanClient,
    DocumentSymbolRequest,
    DocumentSymbolResponse,
)


DUMMY_TEXT = """
theorem foo : True := by
    cases

def bar : Nat := 0
"""


@dataclass
class DummyClient:
    def __init__(self):
        self.client = LeanClient.start(self.root_uri)

    @property
    def root_uri(self) -> str:
        return Path.cwd().resolve().as_uri()

    @property
    def dummy_file(self) -> Path:
        return Path("test.lean").resolve()

    @property
    def dummy_uri(self) -> str:
        return self.dummy_file.as_uri()

    def __enter__(self) -> "DummyClient":
        return self

    def __exit__(self, exc_type: Any, exc_value: Any, traceback: Any) -> None:
        self.client.shutdown()


# def test_is_proved():
#     with DummyClient() as dc:
#         dc.client.open_file(dc.dummy_uri, DUMMY_TEXT)
#         diags = get_per_theorem_errors(dc.client, dc.dummy_uri, DUMMY_TEXT, None)
#         print(dc.client.latest_diagnostics)
#         assert "foo" in diags
#         ts = diags["foo"]
#         bad_diags = [d for d in ts.diagnostics if d.severity == 1]
#         assert len(bad_diags) == 1


def test_document_symbol_request():
    with DummyClient() as dc:
        dc.client.open_file(dc.dummy_uri, DUMMY_TEXT)
        request = DocumentSymbolRequest(uri=dc.dummy_uri)
        response = dc.client.send_request(request)
        assert isinstance(response, DocumentSymbolResponse)
        # assert len(response.symbols) == 2
        # assert response.symbols[0].name == "foo"
        # assert response.symbols[1].name == "bar"


# def test_large_file():
#     """
#     There was an issue where the client wouldn't read all of the
#     content in one call.
#     """
#     NUM_THMS = 200
#     large_file = "\n\n".join(
#         [f"theorem foo{i} : False := by sorry" for i in range(NUM_THMS)]
#     )
#     with DummyClient() as dc:
#         dc.client.open_file(dc.dummy_uri, large_file)
#         request = DocumentSymbolRequest(uri=dc.dummy_uri)
#         response = dc.client.send_request(request)
#         assert isinstance(response, DocumentSymbolResponse)
#         diags = get_per_theorem_diagnostics(
#             dc.client, dc.dummy_uri, large_file, None
#         )
#         assert len(diags) == NUM_THMS
#         for _, diags in diags.items():
#             sorry_diags = [
#                 d
#                 for d in diags.diagnostics
#                 if d.severity == 2 and "sorry" in d.message
#             ]
#             assert len(sorry_diags) == 1
