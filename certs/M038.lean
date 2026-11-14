import ChainOfProof
open ChainOfProof

namespace Cert.M038

def cited : List Fact := [
  ⟨292, .webSearch, 1427133764343210, 1, 165, 159⟩,
  ⟨483, .tag, 1794614400000000, 1, 165, 229⟩ ]

def claim : Claim := .both (Sets.searched 292) (Sets.tagged 292 .obj 483 229)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M038

#print axioms Cert.M038.verified
