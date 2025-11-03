"""
Interface to https://github.com/rkthomps/llm-instruments

Currently the llm-instruments are not inserted into the Lean language server,
instead they are a command line tool.
It would likely be better to integrate them into the language server
"""

import json
from typing import Any
from pathlib import Path
import subprocess

from dataclasses import dataclass

from lean_client.client import Range, LeanClient


@dataclass
class TheoremInfo:
    name: str
    range: Range
    sig_range: Range
    val_range: Range

    @classmethod
    def from_lean_dict(cls, data: Any) -> "TheoremInfo":
        return cls(
            name=data["name"],
            range=Range.from_dict(data["range"]),  # type: ignore
            sig_range=Range.from_dict(data["sigRange"]),  # type: ignore
            val_range=Range.from_dict(data["valRange"]),  # type: ignore
        )


def run_command(
    workspace: Path, command: str, args: list[str]
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["lake", "exe", "llm-instruments", command] + args,
        cwd=workspace,
        capture_output=True,
        text=True,
    )
    return result


class CommandError(Exception):
    pass


@dataclass
class HeartbeatCommand:
    workspace: Path  # Root of Lean project

    def __post_init__(self):
        assert self.workspace.exists()

    @property
    def command_name(self) -> str:
        return "heartbeat"

    @property
    def command_args(self) -> list[str]:
        return []

    def run(self) -> bool:
        """
        Returns True if the heartbeat command succeeds
        Returns False otherwise
        """
        result = run_command(self.workspace, self.command_name, self.command_args)
        return result.returncode == 0


@dataclass
class TheoremInfoCommand:
    workspace: Path  # Root of Lean project
    rel_filepath: Path  # Relative to workspace root

    def __post_init__(self):
        assert self.workspace.exists()
        assert self.file_path.exists()

    @property
    def command_name(self) -> str:
        return "theorem-info"

    @property
    def file_path(self) -> Path:
        return self.workspace / self.rel_filepath

    @property
    def command_args(self) -> list[str]:
        return [str(self.rel_filepath)]

    def run(self) -> list[TheoremInfo] | CommandError:
        result = run_command(self.workspace, self.command_name, self.command_args)
        if result.returncode != 0:
            return CommandError(f"TheoremInfoCommand failed: {result.stderr}")
        return [TheoremInfo.from_lean_dict(item) for item in json.loads(result.stdout)]
