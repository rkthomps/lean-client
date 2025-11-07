from lean_client.client import (
    LeanClient,
    WaitForDiagnosticsRequest,
    WaitForDiagnosticsResponse,
)

from tests.util import INSTR_PROJ_LOC


def test_parallel_clients() -> None:
    NUM_CLIENTS = 2
    uri = INSTR_PROJ_LOC.resolve().as_uri()
    file = "LeanInstrProj/TheoremRanges.lean"
    file_uri = (INSTR_PROJ_LOC / file).resolve().as_uri()
    file_contents = (INSTR_PROJ_LOC / file).read_text()
    clients = [LeanClient.start(INSTR_PROJ_LOC) for _ in range(NUM_CLIENTS)]
    for client in clients:
        client.open_file(file_uri, file_contents)
        request = WaitForDiagnosticsRequest(
            uri=file_uri, version=client.file_version(file_uri)
        )
        assert isinstance(client.send_request(request), WaitForDiagnosticsResponse)
        client.shutdown()
