from pathlib import Path
from typing import Any, Optional, IO

import os
import re
import sys
import time
import json
import select
import signal

import subprocess
import threading
import logging

from psutil import TimeoutExpired
from pydantic import BaseModel

logger = logging.getLogger(__name__)


class Position(BaseModel):
    line: int
    character: int

    def __lt__(self, other: "Position") -> bool:
        if self.line < other.line:
            return True
        elif self.line > other.line:
            return False
        else:
            return self.character < other.character

    def __le__(self, other: "Position") -> bool:
        return self < other or self == other

    def max(self, other: "Position") -> "Position":
        if self < other:
            return other
        else:
            return self

    @property
    def params(self) -> dict[str, int]:
        return {
            "line": self.line,
            "character": self.character,
        }

    @classmethod
    def from_response(cls, data: Any) -> "Position":
        return cls(
            line=data["line"],
            character=data["character"],
        )


class Range(BaseModel):
    start: Position
    end: Position

    def immediately_before(self, other: "Range") -> bool:
        if self.end.line == other.start.line:
            return self.end.character == other.start.character
        if self.end.line + 1 == other.start.line:
            return other.start.character == 0
        return False

    def subsumes(self, other: "Range") -> bool:
        return self.start <= other.start and other.end <= self.end

    def intersect(self, other: "Range") -> bool:
        """
        TODO: Need to test this. Sketchy
        """
        if self.end.line < other.start.line:
            return False
        if self.start.line > other.end.line:
            return False
        ## our end line is >= their start line
        ## our start line is <= their end line
        if self.end.line == other.start.line:
            return self.end.character > other.start.character
        if self.start.line == other.end.line:
            return self.start.character < other.end.character
        return True

    @property
    def params(self) -> dict[str, Any]:
        return {
            "start": self.start.params,
            "end": self.end.params,
        }

    @classmethod
    def from_str(cls, s: str) -> "Range":
        """
        Parses a range from a string of the form "line1:col1-line2:col2"
        where line and col are 0-based.
        """
        match_obj = re.match(r"(\d+):(\d+)-(\d+):(\d+)", s)
        if match_obj is None:
            raise ValueError(f"Invalid range string: {s}")
        start_line, start_col, end_line, end_col = match_obj.groups()
        return cls(
            start=Position(line=int(start_line), character=int(start_col)),
            end=Position(line=int(end_line), character=int(end_col)),
        )

    @classmethod
    def from_response(cls, data: Any) -> "Range":
        return cls(
            start=Position.from_response(data["start"]),
            end=Position.from_response(data["end"]),
        )


class InitializeRequest(BaseModel):
    root_uri: str

    @property
    def params(self):
        return {
            "rootUri": self.root_uri,
        }

    @staticmethod
    def method() -> str:
        return "initialize"


class ShutdownRequest(BaseModel):
    @property
    def params(self) -> dict[Any, Any]:
        return {}

    @staticmethod
    def method() -> str:
        return "shutdown"


class WaitForDiagnosticsRequest(BaseModel):
    uri: str
    version: int

    @staticmethod
    def method() -> str:
        return "textDocument/waitForDiagnostics"

    @property
    def params(self) -> dict[str, Any]:
        return {
            "uri": self.uri,
            "version": self.version,
        }


class DocumentSymbolRequest(BaseModel):
    uri: str

    @staticmethod
    def method() -> str:
        return "textDocument/documentSymbol"

    @property
    def params(self) -> dict[str, Any]:
        return {
            "textDocument": {
                "uri": self.uri,
            }
        }


class PlainGoalRequest(BaseModel):
    uri: str
    position: Position

    @staticmethod
    def method() -> str:
        return "$/lean/plainGoal"

    @property
    def params(self) -> dict[str, Any]:
        return {
            "textDocument": {
                "uri": self.uri,
            },
            "position": self.position.params,
        }


Request = (
    InitializeRequest
    | ShutdownRequest
    | PlainGoalRequest
    | WaitForDiagnosticsRequest
    | DocumentSymbolRequest
)


class InitializedNotification(BaseModel):
    @property
    def params(self) -> dict[Any, Any]:
        return {}

    @staticmethod
    def method() -> str:
        return "initialized"


class ExitNotification(BaseModel):
    @staticmethod
    def method() -> str:
        return "exit"

    @property
    def params(self) -> dict[Any, Any]:
        return {}


class DidOpenNotification(BaseModel):
    uri: str
    text: str
    version: int
    language_id: str

    @staticmethod
    def method() -> str:
        return "textDocument/didOpen"

    @property
    def params(self) -> dict[str, dict[str, int | str]]:
        return {
            "textDocument": {
                "uri": self.uri,
                "text": self.text,
                "languageId": self.language_id,
                "version": self.version,
            }
        }


class ContentChange(BaseModel):
    text: str
    range: Range


class DidChangeNotification(BaseModel):
    uri: str
    version: int
    text: str
    content_changes: Optional[list[ContentChange]]

    @staticmethod
    def method() -> str:
        return "textDocument/didChange"

    @property
    def params(self) -> dict[str, Any]:
        if self.content_changes is not None:
            return {
                "textDocument": {
                    "uri": self.uri,
                    "version": self.version,
                },
                "contentChanges": [
                    {
                        "text": change.text,
                        "range": change.range.params,
                    }
                    for change in self.content_changes
                ],
            }
        else:
            return {
                "textDocument": {
                    "uri": self.uri,
                    "version": self.version,
                },
                "contentChanges": [
                    {
                        "text": self.text,
                        "range": None,
                    }
                ],
            }


ClientNotification = (
    InitializedNotification
    | ExitNotification
    | DidOpenNotification
    | DidChangeNotification
)


class Diagnostic(BaseModel):
    source: str
    severity: int
    range: Range
    message: str
    fullRange: Range

    @classmethod
    def from_response(cls, json: Any) -> "Diagnostic":
        return cls(
            source=json["source"],
            severity=json["severity"],
            range=Range.from_response(json["range"]),
            message=json["message"],
            fullRange=Range.from_response(json["fullRange"]),
        )


class DiagnosticsNotification(BaseModel):
    version: int
    uri: str
    diagnostics: list[Diagnostic]

    @staticmethod
    def method() -> str:
        return "textDocument/publishDiagnostics"

    @classmethod
    def from_response(cls, json: Any) -> "DiagnosticsNotification":
        assert json["method"] == cls.method()
        version: Any = json["params"]["version"]
        uri: Any = json["params"]["uri"]
        diagnostics: Any = json["params"]["diagnostics"]
        return cls(
            version=version,
            uri=uri,
            diagnostics=[Diagnostic.from_response(d) for d in diagnostics],
        )


class RegisterCapabilityNotification(BaseModel):
    @staticmethod
    def method() -> str:
        return "client/registerCapability"

    @classmethod
    def from_response(cls, json: Any) -> "RegisterCapabilityNotification":
        assert json["method"] == cls.method()
        return cls()


class LeanProgressNotification(BaseModel):
    uri: str
    version: int
    processing: list[Range]

    @staticmethod
    def method() -> str:
        return "$/lean/fileProgress"

    def __repr__(self) -> str:
        return f"$/lean/fileProgress {self.uri} {self.version} {self.processing}"

    @classmethod
    def from_response(cls, json: Any) -> "LeanProgressNotification":
        assert json["method"] == cls.method()
        version = json["params"]["textDocument"]["version"]
        uri = json["params"]["textDocument"]["uri"]
        return cls(
            uri=uri,
            version=version,
            processing=[
                Range.from_response(r["range"]) for r in json["params"]["processing"]
            ],
        )


class InlayHintNotification(BaseModel):
    @staticmethod
    def method() -> str:
        return "workspace/inlayHint/refresh"

    @classmethod
    def from_response(cls, json: Any) -> "InlayHintNotification":
        assert json["method"] == cls.method()
        return cls()


class SemanticTokensNotification(BaseModel):

    @staticmethod
    def method() -> str:
        return "workspace/semanticTokens/refresh"

    @classmethod
    def from_response(cls, json: Any) -> "SemanticTokensNotification":
        assert json["method"] == cls.method()
        return cls()


ServerNotification = (
    DiagnosticsNotification
    | LeanProgressNotification
    | RegisterCapabilityNotification
    | InlayHintNotification
    | SemanticTokensNotification
)


class WaitForDiagnosticsResponse(BaseModel):
    id: int

    @classmethod
    def from_response(cls, json: Any) -> "WaitForDiagnosticsResponse":
        id = json["id"]
        return WaitForDiagnosticsResponse(id=id)


class DocumentSymbol(BaseModel):
    name: str
    kind: int
    range: Range
    selectionRange: Range
    children: list["DocumentSymbol"]
    detail: Optional[str]

    @classmethod
    def from_response(cls, json: Any) -> "DocumentSymbol":
        return cls(
            name=json["name"],
            kind=json["kind"],
            range=Range.from_response(json["range"]),
            selectionRange=Range.from_response(json["selectionRange"]),
            children=[cls.from_response(child) for child in json.get("children", [])],
            detail=json.get("detail"),
        )


class DocumentSymbolResponse(BaseModel):
    id: int
    symbols: list[DocumentSymbol]

    @classmethod
    def from_response(cls, json: Any) -> "DocumentSymbolResponse":
        id = json["id"]
        symbols = [DocumentSymbol.from_response(s) for s in json["result"]]
        return cls(
            id=id,
            symbols=symbols,
        )


class InitializedResponse(BaseModel):
    id: int

    @classmethod
    def from_response(cls, json: Any) -> "InitializedResponse":
        id = json["id"]
        return cls(id=id)


class NoGoalResponse(BaseModel):
    id: int

    @classmethod
    def from_response(cls, json: Any) -> "NoGoalResponse":
        id = json["id"]
        return cls(
            id=id,
        )


class PlainGoalResponse(BaseModel):
    id: int
    rendered: str
    goals: list[str]

    @classmethod
    def from_response(cls, json: Any) -> "PlainGoalResponse | NoGoalResponse":
        id = json["id"]
        if "result" not in json or json["result"] is None:
            assert isinstance(id, int)
            return NoGoalResponse(id=id)
        rendered = json["result"]["rendered"]
        goals = json["result"]["goals"]
        return cls(
            id=id,
            rendered=rendered,
            goals=goals,
        )


class ShutdownResponse(BaseModel):
    id: int

    @classmethod
    def from_response(cls, json: Any) -> "ShutdownResponse":
        id = json["id"]
        return cls(id=id)


Response = (
    InitializedResponse
    | PlainGoalResponse
    | NoGoalResponse
    | ShutdownResponse
    | WaitForDiagnosticsResponse
    | DocumentSymbolResponse
)


def get_response_ty(request: Request) -> type[Response]:
    match request:
        case InitializeRequest():
            return InitializedResponse
        case PlainGoalRequest():
            return PlainGoalResponse
        case ShutdownRequest():
            return ShutdownResponse
        case WaitForDiagnosticsRequest():
            return WaitForDiagnosticsResponse
        case DocumentSymbolRequest():
            return DocumentSymbolResponse
        case _:
            raise ValueError(f"Unknown request type: {type(request)}")


def read_response(message: Any) -> Response:
    if "result" in message and "rendered" in message["result"]:
        return PlainGoalResponse.from_response(message)

    logger.info(f"Reading response: {message}")
    return InitializedResponse.from_response(message)


def read_notification(message: Any) -> ServerNotification:
    method = message["method"]
    match method:
        case "textDocument/publishDiagnostics":
            return DiagnosticsNotification.from_response(message)
        case "$/lean/fileProgress":
            return LeanProgressNotification.from_response(message)
        case "client/registerCapability":
            return RegisterCapabilityNotification.from_response(message)
        case "workspace/inlayHint/refresh":
            return InlayHintNotification.from_response(message)
        case "workspace/semanticTokens/refresh":
            return SemanticTokensNotification.from_response(message)
        case _:
            raise ValueError(f"Unknown notification method: {method}")


RPC_VERSION = "2.0"


def read_exactly(stream: IO[bytes], n: int) -> bytes:
    data = bytearray()
    while len(data) < n:
        chunk = stream.read(n - len(data))
        if not chunk:  # EOF
            break
        data.extend(chunk)
    return bytes(data)


def read_lsp_message_header(stream: IO[bytes]) -> int:
    """
    Reads headers from the LSP server until an empty line.
    Returns the Content-Length as an int.
    """
    content_length = None
    while True:
        line = stream.readline().decode("utf-8")
        if not line.strip():  # empty line: end of headers
            break
        match = re.match(r"Content-Length:\s*(\d+)", line)
        if match:
            (content_length_str,) = match.groups()
            content_length = int(content_length_str)
    if content_length is None:
        raise ValueError("No Content-Length header found")
    return content_length


class LeanClient:
    def __init__(self, workspace: Optional[Path]):
        copy_env = os.environ.copy()
        work_dir = workspace if workspace is not None else Path.cwd().resolve()
        if (work_dir / "lakefile.lean").exists() or (
            work_dir / "lakefile.toml"
        ).exists():
            command = ["lake", "serve"]
        else:
            command = ["lean", "--server"]
        self.process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=sys.stderr,
            text=False,
            bufsize=0,
            env=copy_env,
            cwd=work_dir,
            start_new_session=True,
        )
        self.process.stdout
        self.request_id = 0
        self.lock = threading.Lock()
        self.managed_files: dict[str, int] = {}  # uri -> version
        self.latest_diagnostics: dict[str, DiagnosticsNotification] = {}

    def open_file(self, uri: str, text: str, language_id: str = "lean4"):
        assert uri not in self.managed_files, f"File {uri} is already open."
        self.managed_files[uri] = 1
        open_notification = DidOpenNotification(
            uri=uri,
            text=text,
            version=1,
            language_id=language_id,
        )
        self.send_notification(open_notification)

    def is_open(self, uri: str) -> bool:
        return uri in self.managed_files

    def file_version(self, uri: str) -> int:
        """
        Returns the current version of the file.
        """
        assert uri in self.managed_files, f"File {uri} is not open."
        return self.managed_files[uri]

    def change_file(self, uri: str, new_text: str) -> int:
        """
        Updates the file for the lsp and returns the new version number.
        """
        assert uri in self.managed_files, f"File {uri} is not open."
        new_version = self.managed_files[uri] + 1
        self.managed_files[uri] = new_version
        change_notification = DidChangeNotification(
            uri=uri,
            text=new_text,
            version=new_version,
            content_changes=None,
        )
        self.send_notification(change_notification)
        return new_version

    def get_file_diagnostics(self, uri: str) -> Optional[DiagnosticsNotification]:
        """
        Returns the latest diagnostics and version for the given file, if any.
        """
        self.update_diagnostics()
        return self.latest_diagnostics.get(uri, None)

    def wait_for_register(self, timeout: float = 5.0):
        start = time.time()
        while True:
            message = self.read_message(response_ty=None, block=False)
            if isinstance(message, RegisterCapabilityNotification):
                return
            if time.time() - start > timeout:
                raise TimeoutError(
                    "Timed out waiting for register capability notification."
                )

    def wait_for_diagnostics(
        self, uri: str, timeout: float = 5.0
    ) -> DiagnosticsNotification:
        logger.info(
            f"Waiting for diagnostics for {uri} version {self.managed_files.get(uri, 'N/A')}"
        )
        assert uri in self.managed_files, f"File {uri} is not open."
        total_wait = 0.0
        wait_interval = 0.1
        while total_wait < timeout:
            self.update_diagnostics()
            if uri in self.latest_diagnostics:
                diag = self.latest_diagnostics[uri]
                print(f"Got diagnostics: {diag}")
                if diag.version == self.managed_files[uri]:
                    return diag
            time.sleep(wait_interval)
            total_wait += wait_interval
        raise TimeoutError(
            f"Timed out waiting for diagnostics for {uri} version {self.managed_files[uri]}"
        )

    def read_err(self) -> Optional[str]:
        while True:
            assert self.process.stderr is not None, "Process stderr is none."
            ready, _, _ = select.select([self.process.stderr], [], [], 0.1)
            if not ready:
                return None
            line = self.process.stderr.readline().decode()
            if not line.strip():
                break
            logger.error(f"Lean stderr: {line}")
            return line

    def read_message(
        self, response_ty: Optional[type[Response]], block: bool
    ) -> Optional[ServerNotification | Response]:
        while True:
            assert self.process.stdout is not None, "Process stdout is none."
            ready, _, _ = select.select([self.process.stdout], [], [], 0.1)
            if not ready and not block:
                return None

            content_length = read_lsp_message_header(self.process.stdout)
            response = read_exactly(self.process.stdout, content_length)
            assert (
                len(response) == content_length
            ), f"Expected {content_length} bytes, got {len(response)} bytes."
            message = json.loads(response)

            if "method" in message:
                return read_notification(message)
            elif response_ty is not None and "id" in message:
                return response_ty.from_response(message)

    def update_diagnostics(self):
        while True:
            message = self.read_message(response_ty=None, block=False)
            if message is not None:
                logging.debug(f"Read message: {message}")
            if message is None:
                break
            if isinstance(message, DiagnosticsNotification):
                logger.info(f"Adding diagnostics: {message}")
                self.latest_diagnostics[message.uri] = message

    def shutdown(self):
        self.send_request(ShutdownRequest(), timeout=60.0)
        self.send_notification(ExitNotification())
        try:
            if self.process.stdin is not None:
                self.process.stdin.close()
        except Exception as e:
            pass

        try:
            self.process.wait(timeout=2)
            return
        except TimeoutExpired:
            pass

        os.killpg(self.process.pid, signal.SIGTERM)
        try:
            self.process.wait(timeout=0.5)
        except TimeoutExpired:
            # fallback hammer
            os.killpg(self.process.pid, signal.SIGKILL)
            self.process.wait()

    def send_str(self, message: str):
        message_bytes = message.encode("utf-8")
        content_length = len(message_bytes)
        full_message = f"Content-Length: {content_length}\r\n\r\n{message}".encode(
            "utf-8"
        )
        with self.lock:
            assert self.process.stdin is not None, "Process stdin is none."
            logging.debug("=== Sending message to Lean stdin ===")
            logging.debug(full_message.decode("utf-8", errors="replace"))
            self.process.stdin.write(full_message)
            self.process.stdin.flush()

    def send_notification(self, notification: ClientNotification):
        notification_dict: dict[Any, Any] = {
            "jsonrpc": RPC_VERSION,
            "method": notification.method(),
            "params": notification.params,
        }
        message = json.dumps(notification_dict)
        self.send_str(message)

    def send_request(self, request: Request, timeout: float = 10.0) -> Response:
        """
        Potential issue: What if we get a notification in the middle of a request?
        """
        self.request_id += 1
        request_dict: dict[Any, Any] = {
            "jsonrpc": RPC_VERSION,
            "id": self.request_id,
            "method": request.method(),
            "params": request.params,
        }
        message = json.dumps(request_dict)
        self.send_str(message)

        start = time.time()
        response_ty = get_response_ty(request)
        response_data = self.read_message(response_ty=response_ty, block=True)
        if response_data is not None:
            logging.debug(f"Initial read message: {response_data}")
        while response_data is None or isinstance(response_data, ServerNotification):
            if isinstance(response_data, DiagnosticsNotification):
                self.latest_diagnostics[response_data.uri] = response_data
            response_data = self.read_message(response_ty=response_ty, block=True)
            if response_data is not None:
                logging.debug(f"Read message: {response_data}")
            if time.time() - start > timeout:
                raise TimeoutError(
                    f"Timed out waiting for response to {request.method()}"
                )

        assert response_data.id == self.request_id
        return response_data

    @classmethod
    def start(cls, workspace: Path) -> "LeanClient":
        client = cls(workspace)
        logging.debug("Starting Lean client...")
        workspace_uri = workspace.resolve().as_uri()
        client.send_request(InitializeRequest(root_uri=workspace_uri))
        logging.debug("Sent initialize request.")
        time.sleep(0.5)
        client.send_notification(InitializedNotification())
        logging.debug("Sent initialized notification.")
        return client
