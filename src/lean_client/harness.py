"""
A harness for a proof search.
"""

import types
from typing import Optional

import logging
from dataclasses import dataclass
from pathlib import Path

from lean_client.client import (
    Position,
    Range,
    LeanClient,
    Diagnostic,
    WaitForDiagnosticsRequest,
    WaitForDiagnosticsResponse,
)

from lean_client.instruments import (
    HeartbeatCommand,
    TheoremInfoCommand,
    CommandError,
)

from lean_client.lsp_utils import get_range_str

logger = logging.getLogger(__name__)


@dataclass
class ProofSucceededResult:
    pass


@dataclass
class ProofFailedResult:
    diagnostics: list[Diagnostic]


class Harness:
    def __init__(
        self,
        workspace: Path,
        relfile: Path,
        theorem_name: str,
        clear_proof: bool = True,
        clear_file_proofs: bool = False,
    ):
        """
        Args:
            workspace: A path (absolute or relative) to the root of the Lean project.
            file: A path (relative to workspace) to the Lean file containing the theorem.
            theorem_name: The (fully qualified) name of the theorem to be proved.
            clear_proof: Whether to clear the proof of the theorem before attempting to prove it.
            clear_file_proofs: Whether to clear the proofs of all theorems in the file before attempting to prove the target theorem.

        TODO:
        - It might be better to pass in a LeanClient instance instead of creating one here.
        - Then the same LeanClient could be shared across multiple Harness instances.
        - This approach is simpler for now.
        """
        assert workspace.exists()
        assert (workspace / relfile).exists()
        self.workspace = workspace.resolve()
        self.relfile = relfile
        self.orig_file_contents = self.file.read_text()

        self.theorem_name = theorem_name

        logger.info(f"Checking that workspace {self.workspace} supports instruments...")
        heartbeat = HeartbeatCommand(workspace=self.workspace)
        if heartbeat.run():
            logger.info(
                f"Finding theorem info for {theorem_name} in file {self.file}..."
            )
            info_command = TheoremInfoCommand(
                workspace=self.workspace, rel_filepath=self.relfile
            )
            theorem_infos = info_command.run()
            if isinstance(theorem_infos, CommandError):
                raise RuntimeError(
                    f"Failed to get theorem info for {theorem_name} in file {self.file}: {theorem_infos}"
                )
            matching_infos = [
                ti for ti in theorem_infos if ti.name == self.theorem_name
            ]
            if len(matching_infos) != 1:
                raise RuntimeError(
                    f"Expected exactly one theorem info for {theorem_name} in file {self.file}, but found {len(matching_infos)}"
                )
        else:
            raise RuntimeError(
                f"Workspace {self.workspace} currently does not support instruments. "
                f"In the future, we could have partial support for non-instrumented projects."
                f"For now please make sure to install https://github.com/rkthomps/llm-instruments"
            )

        self.theorem_info = matching_infos[0]

        self.client = LeanClient.start(self.workspace_uri)
        self.client.open_file(self.file_uri, self.orig_file_contents)

    @property
    def file(self) -> Path:
        return (self.workspace / self.relfile).resolve()

    @property
    def workspace_uri(self) -> str:
        return self.workspace.resolve().as_uri()

    @property
    def file_uri(self) -> str:
        return (self.workspace / self.relfile).resolve().as_uri()

    def get_file_prefix(self) -> str:
        """
        Get the preifx of the file, including the theorem statement, up to
        the start of the proof.
        """
        prefix_range = Range(
            start=Position(line=0, character=0),
            end=self.theorem_info.val_range.start,
        )
        prefix = get_range_str(self.orig_file_contents, prefix_range)
        return prefix

    def check_proof(self, proof: str) -> ProofSucceededResult | ProofFailedResult:
        new_file_contents = self.get_file_prefix() + proof
        self.client.change_file(self.file_uri, new_file_contents)
        wait_response = self.client.send_request(
            WaitForDiagnosticsRequest(
                uri=self.file_uri, version=self.client.managed_files[self.file_uri]
            )
        )
        assert isinstance(wait_response, WaitForDiagnosticsResponse)
        diagnostics = self.client.latest_diagnostics[self.file_uri].diagnostics
        # TODO: Might have to do the "proof replacement strategy"
        # e.g. if there is a remaining open section or namespace
        # that might trigger an error here but is not really a proof error.
        # so we need to find where the proof ends.
        proof_diagnostics = [
            d for d in diagnostics if self.theorem_info.range.start <= d.range.end
        ]
        proof_sorry_diagnostics = [
            d
            for d in proof_diagnostics
            if d.severity == 2 and "declaration uses 'sorry'" in d.message
        ]
        if len(proof_sorry_diagnostics) > 0:
            """
            Here the proof failed because it used 'sorry'.
            So the prefix including the last sorry can be learned.
            """
            return ProofFailedResult(diagnostics=proof_diagnostics)

        proof_error_diagnostics = [d for d in proof_diagnostics if d.severity == 1]
        if len(proof_error_diagnostics) == 0:
            return ProofSucceededResult()
        else:
            return ProofFailedResult(diagnostics=proof_diagnostics)

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[types.TracebackType],
    ) -> Optional[bool]:
        self.client.shutdown()
        return True
