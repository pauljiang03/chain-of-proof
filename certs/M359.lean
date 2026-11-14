import ChainOfProof
open ChainOfProof

namespace Cert.M359

def cited : List Fact := [
  ⟨12729, .fileContent, 1794614400000000, 1, 108, 16152⟩,
  ⟨12780, .fileContent, 1794614400000000, 1, 142, 16152⟩,
  ⟨12786, .fileContent, 1794614400000000, 1, 143, 16152⟩ ]

def claim : Claim := .both (Sets.sameContent 12729 12780) (Sets.sameContent 12780 12786)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M359

#print axioms Cert.M359.verified
