"""
A harness for a proof search.
"""

import re
import types
from typing import Optional

import logging
import threading
from pydantic import BaseModel
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


class ProofSucceededResult(BaseModel):
    pass


class InvalidPrefix(BaseModel):
    attempted_proof: str
    prefix: str
    source_error: Diagnostic


class ProofFailedResult(BaseModel):
    learned_prefix: Optional[InvalidPrefix]
    diagnostics: list[Diagnostic]


STARTUP_LOCK = threading.Semaphore(8)

# Map of workspace path to LeanClient instance.
CLIENT_MAP: dict[Path, LeanClient] = {}

# Set of open file uris.
FILE_SET: set[Path] = set()


class Harness:
    def __init__(
        self,
        workspace: Path,
        relfile: Path,
        theorem_name: str,
        clear_proof: bool = True,
        clear_file_proofs: bool = False,
        timeout: float = 120,
    ):
        """
        Args:
            workspace: A path (absolute or relative) to the root of the Lean project.
            file: A path (relative to workspace) to the Lean file containing the theorem.
            theorem_name: The (fully qualified) name of the theorem to be proved.
            clear_proof: Whether to clear the proof of the theorem before attempting to prove it.
            clear_file_proofs: Whether to clear the proofs of all theorems in the file before attempting to prove the target theorem.
            timeout: The timeout (in seconds) for Initial Diagnostics request.

        TODO:
        - It might be better to pass in a LeanClient instance instead of creating one here.
        - Then the same LeanClient could be shared across multiple Harness instances.
        - This approach is simpler for now.
        """
        assert workspace.exists()
        assert (workspace / relfile).exists()
        self.workspace = workspace.resolve()
        self.relfile = relfile

        if clear_file_proofs:
            raise NotImplementedError(
                "Clearing all proofs in the file is not yet implemented."
            )

        self.theorem_name = theorem_name

        logger.info(f"Checking that workspace {self.workspace} supports instruments...")
        with STARTUP_LOCK:
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

            # Simply
            orig_file_contents = self.file.read_text()
            if clear_proof:
                self.orig_file_contents = (
                    self.get_prefix_core(orig_file_contents) + " := by sorry\n"
                )
            else:
                raise NotImplementedError(
                    "Not yet implemented: keeping the original proof."
                )

            self.client = LeanClient.start(self.workspace)
            self.client.open_file(self.file_uri, self.orig_file_contents)
            response = self.client.send_request(
                WaitForDiagnosticsRequest(
                    uri=self.file_uri, version=self.client.file_version(self.file_uri)
                ),
                timeout=timeout,
            )
            assert isinstance(response, WaitForDiagnosticsResponse)

    @property
    def file(self) -> Path:
        return (self.workspace / self.relfile).resolve()

    @property
    def workspace_uri(self) -> str:
        return self.workspace.resolve().as_uri()

    @property
    def file_uri(self) -> str:
        return (self.workspace / self.relfile).resolve().as_uri()

    def get_prefix_core(self, contents: str) -> str:
        prefix_range = Range(
            start=Position(line=0, character=0),
            end=self.theorem_info.sig_range.end,
        )
        prefix = get_range_str(contents, prefix_range)
        return prefix

    def get_theorem_context(self) -> str:
        theorem_start_line = self.theorem_info.range.start.line
        lines = self.orig_file_contents.splitlines()
        context_lines = lines[:theorem_start_line]
        return "\n".join(context_lines)

    def get_file_prefix(self) -> str:
        """
        Get the preifx of the file, including the theorem statement, up to
        the start of the proof.
        """
        return self.get_prefix_core(self.orig_file_contents)

    def get_full_theorem_signature(self) -> str:
        """
        Get the signature of the theorem as defined by the ranges returned
        by Lean.
        """
        # The sig_range begins at the _type signature_ and not the beginning of
        # the declaration.
        full_sig_range = Range(
            start=self.theorem_info.range.start, end=self.theorem_info.sig_range.end
        )
        return get_range_str(self.orig_file_contents, full_sig_range)

    def get_type_signature(self) -> str:
        """
        Get the signature of the theorem as defined by the ranges returned
        by Lean.
        """
        # The sig_range begins at the _type signature_ and not the beginning of
        # the declaration.
        return get_range_str(self.orig_file_contents, self.theorem_info.sig_range)

    def get_error_diagnostics(self) -> list[Diagnostic]:
        latest_diags = self.client.latest_diagnostics[self.file_uri].diagnostics
        proof_diagnostics = [
            d for d in latest_diags if self.theorem_info.range.start <= d.range.end
        ]
        proof_error_diagnostics = [d for d in proof_diagnostics if d.severity == 1]
        return proof_error_diagnostics

    def get_learned_prefix_from_error(
        self, file_contents: str, attempted_proof: str, error: Diagnostic
    ) -> Optional[InvalidPrefix]:
        """
        An easy heuristic to get an "invalid prefix" from an error.
        Here, we take the prefix of a proof up to an error position.
        We also exclude error messages like "unsolved goals" since these
        do not indicate an invalid prefix.
        Instead, they indicate that the proof is incomplete.

        Note that this implementation is a bit naive.
        For example, it erroniously finds an invalid prefix in the following
        proofs:

        theorem foo : True := by
          sim -- error at 'sim' (incomplete tactic)

        theorem bar : True := by
          exact -- need to apply exact to a term
        """
        if re.search(r"Alternative .*? has not been provided", error.message):
            return None

        if re.search(r"unsolved goals", error.message):
            return None

        error_end_pos = error.range.end  # Might have to add one
        error_end_str = get_range_str(
            file_contents, Range(start=Position(line=0, character=0), end=error_end_pos)
        )
        assert error_end_str.startswith(self.get_file_prefix())
        invalid_prefix = error_end_str[len(self.get_file_prefix()) :]
        assert attempted_proof.startswith(invalid_prefix)
        invalid_prefix = InvalidPrefix(
            attempted_proof=attempted_proof,
            prefix=invalid_prefix,
            source_error=error,
        )
        return invalid_prefix

    def get_learned_prefix(
        self, file_contents: str, attempted_proof: str, errors: list[Diagnostic]
    ) -> Optional[InvalidPrefix]:
        invalid_candidates = [
            self.get_learned_prefix_from_error(file_contents, attempted_proof, e)
            for e in errors
        ]
        true_candidates = [c for c in invalid_candidates if c is not None]
        if len(true_candidates) == 0:
            return None
        # Return the shortest invalid prefix
        return min(true_candidates, key=lambda c: len(c.prefix))

    def check_proof(
        self, proof: str, timeout: float = 10.0
    ) -> ProofSucceededResult | ProofFailedResult:
        new_file_contents = self.get_file_prefix() + proof
        print("checking proof: ", new_file_contents)
        self.client.change_file(self.file_uri, new_file_contents)
        wait_response = self.client.send_request(
            WaitForDiagnosticsRequest(
                uri=self.file_uri, version=self.client.managed_files[self.file_uri]
            ),
            timeout,
        )
        assert isinstance(wait_response, WaitForDiagnosticsResponse)
        diagnostics = self.client.latest_diagnostics[self.file_uri].diagnostics

        proof_diagnostics = [
            d for d in diagnostics if self.theorem_info.range.start <= d.range.end
        ]
        proof_error_diagnostics = [d for d in proof_diagnostics if d.severity == 1]
        if 0 < len(proof_error_diagnostics):
            learned_prefix = self.get_learned_prefix(
                file_contents=new_file_contents,
                attempted_proof=proof,
                errors=proof_error_diagnostics,
            )
            return ProofFailedResult(
                learned_prefix=learned_prefix, diagnostics=proof_diagnostics
            )

        proof_sorry_diagnostics = [
            d
            for d in proof_diagnostics
            if d.severity == 2 and "declaration uses 'sorry'" in d.message
        ]
        if 0 < len(proof_sorry_diagnostics):
            """
            Here the proof failed because it used 'sorry'.
            So the prefix including the last sorry can be learned.
            """
            return ProofFailedResult(diagnostics=proof_diagnostics, learned_prefix=None)

        return ProofSucceededResult()

    def __enter__(self):
        return self

    def __exit__(
        self,
        exc_type: Optional[type[BaseException]],
        exc_value: Optional[BaseException],
        traceback: Optional[types.TracebackType],
    ) -> Optional[bool]:
        self.client.shutdown()
        return None
