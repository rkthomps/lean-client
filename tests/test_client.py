from typing import Optional
from dataclasses import dataclass
from http import client
from pathlib import Path
import textwrap
import logging
from typing import Any

import pytest
from tests.util import INSTR_PROJ_LOC

from lean_client.client import (
    LeanClient,
    WaitForDiagnosticsRequest,
    WaitForDiagnosticsResponse,
    FindTheoremsRequest,
    FindTheoremsResponse,
)

from tests.util import BuildError

logger = logging.getLogger(__name__)


DUMMY_TEXT = """
theorem foo : True := by
    cases

def bar : Nat := 0
"""


@dataclass
class DummyClient:
    def __init__(self):
        self.client = LeanClient.start(self.workspace, instrument_server=False)

    @property
    def workspace(self) -> Path:
        return Path.cwd().resolve()

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


def test_find_theorems_request():
    with DummyClient() as dc:
        dc.client.open_file(dc.dummy_uri, DUMMY_TEXT)
        wait_request = WaitForDiagnosticsRequest(
            uri=dc.dummy_uri, version=dc.client.file_version(dc.dummy_uri)
        )
        wait_response = dc.client.send_request(wait_request)
        assert isinstance(wait_response, WaitForDiagnosticsResponse)
        # request = FindTheoremsRequest(uri=dc.dummy_uri)
        # response = dc.client.send_request(request)
        # assert isinstance(response, FindTheoremsResponse)
        # assert len(response.symbols) == 2
        # assert response.symbols[0].name == "foo"
        # assert response.symbols[1].name == "bar"


def test_batteries_document_symbol_request(build_projects: Optional[BuildError]):
    if build_projects is not None:
        pytest.fail(str(build_projects))

    uri = INSTR_PROJ_LOC.resolve().as_uri()
    client = LeanClient.start(INSTR_PROJ_LOC, instrument_server=True)
    file = INSTR_PROJ_LOC / "LeanInstrProj" / "BatteryStuff.lean"
    # file = INSTR_PROJ_LOC / "LeanInstrProj" / "Harness.lean"
    file_uri = file.resolve().as_uri()
    try:
        client.open_file(file_uri, file.read_text())
        wait_request = WaitForDiagnosticsRequest(
            uri=file_uri, version=client.file_version(file_uri)
        )
        wait_response = client.send_request(wait_request)
        assert isinstance(wait_response, WaitForDiagnosticsResponse)
        diags = client.latest_diagnostics[file_uri]
        print(f"Diagnostics: {diags.diagnostics}")
        request = FindTheoremsRequest(uri=file_uri)
        response = client.send_request(request)
        assert isinstance(response, FindTheoremsResponse)
        assert len(response.theorems) == 1
        assert response.theorems[0].name == "rat_to_float"
    finally:
        client.shutdown()


if __name__ == "__main__":
    test_batteries_document_symbol_request(None)
