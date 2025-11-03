import pytest

from typing import Optional
from tests.util import INSTR_PROJ_LOC, NO_INSTR_PROJ_LOC, BuildError
from pathlib import Path

from lean_client.client import Range, Position
from lean_client.instruments import (
    HeartbeatCommand,
    TheoremInfoCommand,
    TheoremInfo,
    CommandError,
)


def test_instr_heartbeat_success(build_projects: Optional[BuildError]) -> None:
    if build_projects is not None:
        pytest.fail(str(build_projects))
    cmd = HeartbeatCommand(workspace=INSTR_PROJ_LOC)
    assert cmd.run() is True


def test_instr_heartbeat_failure(build_projects: Optional[BuildError]) -> None:
    if build_projects is not None:
        pytest.fail(str(build_projects))
    cmd = HeartbeatCommand(workspace=NO_INSTR_PROJ_LOC)
    assert cmd.run() is False


def test_theorem_info(build_projects: Optional[BuildError]) -> None:
    if build_projects is not None:
        pytest.fail(str(build_projects))

    cmd = TheoremInfoCommand(
        workspace=INSTR_PROJ_LOC,
        rel_filepath=Path("LeanInstrProj/TheoremRanges.lean"),
    )

    result = cmd.run()

    if isinstance(result, CommandError):
        pytest.fail(f"TheoremInfoCommand failed: {result}")

    expected = [
        TheoremInfo(
            name="Cat.Cherry.cat",
            range=Range.from_str("21:0-22:9"),
            sig_range=Range.from_str("21:17-21:31"),
            val_range=Range.from_str("21:32-22:9"),
        ),
        TheoremInfo(
            name="foo",
            range=Range.from_str("26:0-27:9"),
            sig_range=Range.from_str("26:12-26:18"),
            val_range=Range.from_str("26:19-27:9"),
        ),
        TheoremInfo(
            name="bar",
            range=Range.from_str("30:0-31:7"),
            sig_range=Range.from_str("30:12-30:19"),
            val_range=Range.from_str("30:20-31:7"),
        ),
    ]
    assert result == expected


if __name__ == "__main__":
    pytest.main([__file__])
