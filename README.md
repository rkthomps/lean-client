
# A Lean LSP Client in Python
This client is a useful way to extract information from the  
Lean language server. 

## Partner Lean Package
To use this package for any Lean project, you need to install 
the instrumentation package in the Lean project:
https://github.com/rkthomps/llm-instruments.
In the future this may not be necessary, but this offers more flexibility in what information we can get from Lean.



## Proof Checking Harness 
Most usefully, this package contains a harness for checking proofs for  
a theorem and returning errors/diagnostics.  
One can use the harness as follows:
```python
from pathlib import Path
from lean_client.harness import Harness, ProofSucceededResult, ProofFailedResult

with Harness(
    workspace="tests/test-data/lean-instr-proj",
    relfile=Path("LeanInstrProj/Harness.lean"),
    theorem_name="foo", # theorem foo : True 
) as harness:
    # Failing proof 
    result_contradiction = harness.check_proof(" := by contradiction")
    assert isinstance(result_contradiction, ProofFailedResult)
    print(result_contradiction.diagnostics) # diagnostics including errors

    # Successful proof
    result_trivial = harness.check_proof(" := by trivial")
    assert isinstance(result_trivial, ProofSucceededResult)
```
