from pathlib import Path

INSTR_PROJ_LOC = Path("tests/test-data/lean-instr-proj")
NO_INSTR_PROJ_LOC = Path("tests/test-data/lean-no-instr-proj")


class BuildError(Exception):
    pass
