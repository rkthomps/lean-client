import pytest

from typing import Optional
from tests.util import INSTR_PROJ_LOC, NO_INSTR_PROJ_LOC, BuildError
from pathlib import Path

from lean_client.client import Range, ProofSampleArguments
from lean_client.instruments import (
    HeartbeatCommand,
    TheoremInfoCommand,
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

    samples = [
        ProofSampleArguments.depth(0.25),
        ProofSampleArguments.depth(0.5),
        ProofSampleArguments.depth(0.75),
        ProofSampleArguments.breadth(0.25),
        ProofSampleArguments.breadth(0.5),
        ProofSampleArguments.breadth(0.75),
    ]

    cmd = TheoremInfoCommand(
        workspace=INSTR_PROJ_LOC,
        rel_filepath=Path("LeanInstrProj/TheoremRanges.lean"),
        samples=samples,
    )

    result = cmd.run()

    if isinstance(result, CommandError):
        pytest.fail(f"TheoremInfoCommand failed: {result}")

    assert len(result) == 3
    assert result[0].name == "Cat.Cherry.cat"
    assert result[0].range == Range.from_str("21:0-22:9")
    assert result[0].sig_range == Range.from_str("21:17-21:31")
    assert result[0].val_range == Range.from_str("21:32-22:9")
    assert result[0].bag_of_tactics is not None and len(result[0].bag_of_tactics) > 0
    assert result[0].samples is not None and len(result[0].samples) > 0
    assert result[0].num_expands is not None

    assert result[1].name == "foo"
    assert result[1].range == Range.from_str("26:0-27:9")
    assert result[1].sig_range == Range.from_str("26:12-26:18")
    assert result[1].val_range == Range.from_str("26:19-27:9")
    assert result[1].bag_of_tactics is not None and len(result[1].bag_of_tactics) > 0
    assert result[1].samples is not None and len(result[1].samples) > 0
    assert result[1].num_expands is not None

    assert result[2].name == "bar"
    assert result[2].range == Range.from_str("30:0-31:7")
    assert result[2].sig_range == Range.from_str("30:12-30:19")
    assert result[2].val_range == Range.from_str("30:20-31:7")
    assert result[2].bag_of_tactics is not None
    assert result[2].samples is not None and len(result[2].samples) > 0
    assert result[2].num_expands is not None


if __name__ == "__main__":
    pytest.main([__file__])
