from typing import Optional

import pytest
import shutil
import subprocess

from tests.util import INSTR_PROJ_LOC, NO_INSTR_PROJ_LOC, BuildError


@pytest.fixture(scope="session")
def lake_available() -> bool:
    """Check if 'lake' is available in the system PATH."""
    return shutil.which("lake") is not None


@pytest.fixture(scope="session")
def build_projects(lake_available: bool) -> None | BuildError:
    """Build test Lean projects using 'lake' if available."""
    if not lake_available:
        return BuildError("Lake is not available in the system PATH.")
    if lake_available:
        for proj in [
            INSTR_PROJ_LOC,
            NO_INSTR_PROJ_LOC,
        ]:
            update_result = subprocess.run(["lake", "update"], cwd=proj)
            if update_result.returncode != 0:
                return BuildError(f"Failed to update Lake dependencies in {proj}")

            build_result = subprocess.run(["lake", "build"], cwd=proj)
            if build_result.returncode != 0:
                return BuildError(f"Failed to build Lean project at {proj}")
