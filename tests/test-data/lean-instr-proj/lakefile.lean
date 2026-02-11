import Lake
open Lake DSL


package «lean-instr-proj» where

require batteries from git
  "https://github.com/leanprover-community/batteries" @ "v4.14.0"

require «llm-instruments» from git "https://github.com/rkthomps/llm-instruments" @ "mod-lsp-4.10"
-- require «llm-instruments» from "/Users/kyle/research/data-collection/lean-llm-instruments/llm-instruments"


lean_lib LeanInstrProj

@[default_target]
lean_exe «lean-instr-proj» {
  root := `Main
  supportInterpreter := true
}
