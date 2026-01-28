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
def build_instr_proj(lake_available: bool) -> None | BuildError:
    if not lake_available:
        return BuildError("Lake is not available in the system PATH.")
    update_result = subprocess.run(
        ["lake", "update", "«llm-instruments»"], cwd=INSTR_PROJ_LOC
    )
    if update_result.returncode != 0:
        return BuildError(f"Failed to update Lake dependencies in {INSTR_PROJ_LOC}")

    build_result = subprocess.run(
        ["lake", "build", "«llm-instruments»"], cwd=INSTR_PROJ_LOC)
    if build_result.returncode != 0:
        return BuildError(f"Failed to build Lean project at {INSTR_PROJ_LOC}")
    build_result = subprocess.run(
        ["lake", "build", "llm-instruments-server"], cwd=INSTR_PROJ_LOC)
    if build_result.returncode != 0:
        return BuildError(f"Failed to build Lean project at {INSTR_PROJ_LOC}")


@pytest.fixture(scope="session")
def build_no_instr_proj(lake_available: bool) -> None | BuildError:
    if not lake_available:
        return BuildError("Lake is not available in the system PATH.")
    update_result = subprocess.run(
        ["lake", "update"], cwd=NO_INSTR_PROJ_LOC
    )
    if update_result.returncode != 0:
        return BuildError(f"Failed to update Lake dependencies in {NO_INSTR_PROJ_LOC}")

    build_result = subprocess.run(
        ["lake", "build"], cwd=NO_INSTR_PROJ_LOC)
    if build_result.returncode != 0:
        return BuildError(f"Failed to build Lean project at {NO_INSTR_PROJ_LOC}")


@pytest.fixture(scope="session")
def build_projects(build_instr_proj: None | BuildError, build_no_instr_proj: None | BuildError) -> None | BuildError:
    """Build test Lean projects using 'lake' if available."""
    if build_instr_proj is not None:
        return build_instr_proj
    if build_no_instr_proj is not None:
        return build_no_instr_proj
    return None
