# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
# Install dependencies
uv sync --dev

# Run all tests
pytest

# Run a single test
pytest tests/test_harness.py::test_proof_foo_result

# Run tests with verbose output
pytest -v
```

Tests require `lake` (Lean's build tool) to be installed. The test fixtures automatically build the Lean test projects in `tests/test-data/` before running.

## Architecture

This is a Python LSP client for the Lean theorem prover, used to extract information and check proofs programmatically.

### Key dependency: llm-instruments

The package requires the [llm-instruments](https://github.com/rkthomps/llm-instruments) Lean package installed in any target Lean project. This provides custom LSP extensions (`$/lean/findTheorems`) and a CLI tool (`lake exe llm-instruments`) not available in the standard Lean LSP.

### Module structure

- **`client.py`** — Core LSP communication layer. `LeanClient` manages a subprocess (`lake serve` or `lean --server`), sends JSON-RPC messages, and receives responses/notifications. All LSP message types (requests, notifications, responses) are defined as Pydantic models here. Use `LeanClient.start(workspace)` as a context manager.

- **`instruments.py`** — Interface to the `llm-instruments` CLI tool. `HeartbeatCommand` checks if the workspace has instruments installed; `TheoremInfoCommand` retrieves theorem ranges (full range, signature range, value range) by running `lake exe llm-instruments theorem-info <file>`.

- **`harness.py`** — High-level proof-checking API. `Harness` combines `LeanClient` + `instruments` to allow iterative proof checking against a specific theorem. On initialization it: (1) retrieves theorem info via instruments, (2) strips the original proof to `sorry`, (3) opens the file with the LSP, (4) waits for initial diagnostics. Then `check_proof(proof_str)` replaces the file content and returns `ProofSucceededResult` or `ProofFailedResult`.

- **`lsp_utils.py`** — Text manipulation utilities: `get_range_str` extracts a substring by LSP `Range`, `str_to_pos` converts a string to its end `Position`, `parse_lean_docstring` parses `/-- ... -/` docstrings.

- **`theorem_utils.py`** — Filters `Diagnostic` lists by range (used to isolate errors belonging to a specific theorem).

### LSP flow

`LeanClient` communicates over stdin/stdout with a Lean server process. The key non-standard methods are:
- `$/lean/findTheorems` — returns structured `TheoremInfo` (ranges for the full theorem, signature, and value)
- `$/lean/plainGoal` — returns proof state goals at a position
- `textDocument/waitForDiagnostics` — blocks until Lean finishes elaborating a file version

Positions and ranges are 0-based (line, character). `TheoremInfo` has three ranges: `range` (full declaration including docstring), `sig_range` (just the type signature), `val_range` (the proof body).

### Test data

`tests/test-data/lean-instr-proj/` — A Lean project with `llm-instruments` as a dependency. Primary test file is `LeanInstrProj/Harness.lean` containing theorems `foo` and `Cat.bat`.

`tests/test-data/lean-no-instr-proj/` — A Lean project without instruments, used for testing fallback behavior.
