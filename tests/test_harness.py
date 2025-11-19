from typing import Optional
import pytest
import textwrap
from pathlib import Path

from lean_client.harness import Harness, ProofSucceededResult, ProofFailedResult

from tests.util import INSTR_PROJ_LOC, NO_INSTR_PROJ_LOC, BuildError


def test_proof_foo_result(build_projects: Optional[BuildError]) -> None:
    """
    Tests proofs for the theorem:
    theorem foo : True := by sorry
    """
    if build_projects is not None:
        pytest.fail(str(build_projects))

    proof_trivial = " := by trivial"

    proof_simp = """ := by
      simp
    """
    proof_simp = textwrap.dedent(proof_simp)

    proof_sorry = """ := by
      sorry
    """
    proof_sorry = textwrap.dedent(proof_sorry)

    proof_contradiction = """ := by
      contradiction
    """
    proof_contradiction = textwrap.dedent(proof_contradiction)

    with Harness(
        workspace=INSTR_PROJ_LOC,
        relfile=Path("LeanInstrProj/Harness.lean"),
        theorem_name="foo",
    ) as harness:
        assert harness.orig_file_contents.endswith("theorem foo : True := by sorry\n")

        result_trivial = harness.check_proof(proof_trivial)
        assert isinstance(result_trivial, ProofSucceededResult)

        result_simp = harness.check_proof(proof_simp)
        assert isinstance(result_simp, ProofSucceededResult)

        result_sorry = harness.check_proof(proof_sorry)
        assert isinstance(result_sorry, ProofFailedResult)

        result_contradiction = harness.check_proof(proof_contradiction)
        assert isinstance(result_contradiction, ProofFailedResult)


def test_proof_bat_result(build_projects: Optional[BuildError]) -> None:
    """
    Tests proofs for the theorem:
    namespace Cat

    theorem bat (a b : Nat) : a + b = b + a := by
      sorry
    """
    if build_projects is not None:
        pytest.fail(str(build_projects))

    proof_trivial = " := by trivial"

    proof_omega = """ := by
      omega
    """
    proof_omega = textwrap.dedent(proof_omega)

    with Harness(
        workspace=INSTR_PROJ_LOC,
        relfile=Path("LeanInstrProj/Harness.lean"),
        theorem_name="Cat.bat",
    ) as harness:
        print("harness initialized")
        result_trivial = harness.check_proof(proof_trivial)
        assert isinstance(result_trivial, ProofFailedResult)
        error_messages = [
            d.message for d in result_trivial.diagnostics if d.severity == 1
        ]
        assert len(error_messages) > 0

        result_omega = harness.check_proof(proof_omega)
        assert isinstance(result_omega, ProofSucceededResult)
        assert (
            harness.get_full_theorem_signature()
            == "theorem bat (a b : Nat) : a + b = b + a"
        )
        assert harness.get_type_signature() == "(a b : Nat) : a + b = b + a"
