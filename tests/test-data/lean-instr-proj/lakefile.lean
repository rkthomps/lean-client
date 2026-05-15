import Lake
open Lake DSL


package «lean-instr-proj» where

require batteries from git
  "https://github.com/leanprover-community/batteries" @ "v4.28.0"

require «llm-instruments» from git "https://github.com/rkthomps/llm-instruments" @ "4.27.0"
-- require «llm-instruments» from "/Users/kyle/research/data-collection/lean-llm-instruments/llm-instruments"


lean_lib LeanInstrProj

@[default_target]
lean_exe «lean-instr-proj» {
  root := `Main
  supportInterpreter := true
}
