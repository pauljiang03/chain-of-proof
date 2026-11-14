import ChainOfProof
open ChainOfProof

namespace Cert.A053

def cited : List Fact := [
  ⟨252, .webSearch, 1427134695855272, 1, 150, 125⟩ ]

def claim : Claim := Sets.searched 252

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A053

#print axioms Cert.A053.verified
