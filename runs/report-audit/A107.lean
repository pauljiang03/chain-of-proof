import ChainOfProof
open ChainOfProof

namespace Cert.A107

def cited : List Fact := [
  ⟨248, .webSearch, 1427134544517540, 1, 147, 125⟩ ]

def claim : Claim := Sets.searched 248

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A107

#print axioms Cert.A107.verified
