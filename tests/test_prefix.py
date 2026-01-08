import pytest
from pathlib import Path
from typing import Optional

from lean_client.harness import Harness, ProofSucceededResult, ProofFailedResult


from tests.util import INSTR_PROJ_LOC, NO_INSTR_PROJ_LOC, BuildError


def test_prefix_1(build_projects: Optional[BuildError]) -> None:
    """
    Tests the case where there are more cases to add:
    ```
    theorem prefix1 (Γ : String → Nat) (e : Exp) :
      eval Γ (cfold e) = eval Γ e := by
      induction e using cfold.induct with
      | case1 => simp [cfold]
    ```
    """

    if build_projects is not None:
        pytest.fail(str(build_projects))

    # fmt: off
    proof1 = (
        " := by\n"
        "  induction e using cfold.induct with\n"
        "  | case1 => simp [cfold]"
    )
    # fmt: on

    with Harness(
        workspace=INSTR_PROJ_LOC,
        relfile=Path("LeanInstrProj/Prefix.lean"),
        theorem_name="prefix1",
    ) as harness:
        result = harness.check_proof(proof1)
        assert isinstance(result, ProofFailedResult)
        assert result.learned_prefix is None


def test_prefix_2(build_projects: Optional[BuildError]) -> None:
    """
    Tests the case where there are more cases to add:
    ```
    theorem prefix2 (Γ : String → Nat) (e : Exp) :
    eval Γ (cfold e) = eval Γ e := by
    induction e using cfold.induct with
    | case1 => simp [cfold]
    | case2 => simp [cfold]
    | case3 => sorry
    | case4 => simp [cfold]
    ```
    """

    if build_projects is not None:
        pytest.fail(str(build_projects))

    # fmt: off
    proof = (
        " := by\n"
        "  induction e using cfold.induct with\n"
        "  | case1 => simp [cfold]\n"
        "  | case2 => simp [cfold]\n"
        "  | case3 => sorry\n"
        "  | case4 => simp [cfold]"
    )
    # fmt: on

    with Harness(
        workspace=INSTR_PROJ_LOC,
        relfile=Path("LeanInstrProj/Prefix.lean"),
        theorem_name="prefix1",
    ) as harness:
        result = harness.check_proof(proof)
        assert isinstance(result, ProofFailedResult)
        assert result.learned_prefix is None


def test_prefix3(build_projects: Optional[BuildError]) -> None:
    """
    Tests a "normal" case where there is an actual learned prefix:

    theorem prefix3 (Γ : String → Nat) (e : Exp) :
    eval Γ (cfold e) = eval Γ e := by
    induction e using cfold.induct e with
    | case1 => simp [cfold]
    | case2 => simp [cfold]
    | case3 => sorry
    | case4 => simp [cfold]
    """
    if build_projects is not None:
        pytest.fail(str(build_projects))

    # fmt: off
    proof = (
        " := by\n"
        "  induction e using cfold.induct e with\n"
        "  | case1 => simp [cfold]\n"
        "  | case2 => simp [cfold]\n"
        "  | case3 => sorry\n"
        "  | case4 => simp [cfold]"
    )
    # fmt: on

    with Harness(
        workspace=INSTR_PROJ_LOC,
        relfile=Path("LeanInstrProj/Prefix.lean"),
        theorem_name="prefix1",
    ) as harness:
        result = harness.check_proof(proof)
        assert isinstance(result, ProofFailedResult)
        assert result.learned_prefix is not None
        assert (
            result.learned_prefix.prefix == " := by\n  induction e using cfold.induct e"
        )


def test_prefix4(build_projects: Optional[BuildError]) -> None:
    """
    Tests a case where the learned prefix coincides with the end of a tactic sequence.
    As an approximate solution, we do not emit any learned prefixes when the errors
    coincide with the end of the LLM-generated string.

    This is not ideal. Consider the following examples:

    ```
    def bar : True := by trivial

    -- In this case, you know the tactic is done
    thoerem ex1 : False := by
      simp [bar]

    -- In this case, simp doesn't work, but perhaps simp [...]  would work
    theorem ex2 (n : Nat) : P := by
      induction n with
      | zero => simp
      | succ n ih => ...
    ```

    theorem prefix4 (Γ : String → Nat) (e : Exp) :
    eval Γ (cfold e) = eval Γ e := by
    s
    """
    if build_projects is not None:
        pytest.fail(str(build_projects))

    # fmt: off
    proof = (
        " := by\n"
        "  sim"
    )
    # fmt: on

    with Harness(
        workspace=INSTR_PROJ_LOC,
        relfile=Path("LeanInstrProj/Prefix.lean"),
        theorem_name="prefix1",
    ) as harness:
        result = harness.check_proof(proof)
        assert isinstance(result, ProofFailedResult)
        assert result.learned_prefix is None
