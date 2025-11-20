import psutil
import pytest
from pathlib import Path

from lean_client.harness import Harness, ProofSucceededResult
from tests.util import INSTR_PROJ_LOC, NO_INSTR_PROJ_LOC


def count_lean_processes():
    return sum(
        "lean" in p.name() or "lake" in p.name() for p in psutil.process_iter(["name"])  # type: ignore
    )


@pytest.mark.skip(
    reason="Not reliable. Could be other lean processes in the environment. Good for manual testing."
)
def test_shutdown_leak() -> None:
    initial_lean_process_count = count_lean_processes()
    print(f"Initial Lean process count: {initial_lean_process_count}")

    # Run multiple harness contexts to see if any Lean processes are leaked.
    for i in range(2):
        with Harness(
            workspace=INSTR_PROJ_LOC,
            relfile=Path("LeanInstrProj/Harness.lean"),
            theorem_name="Cat.bat",
        ) as harness:
            harness.check_proof(" := by trivial")
            current_lean_process_count = count_lean_processes()
            assert current_lean_process_count >= 2

    print("End", count_lean_processes())


if __name__ == "__main__":
    test_shutdown_leak()
