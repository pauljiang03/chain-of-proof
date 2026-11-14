import ChainOfProof
open ChainOfProof

namespace Cert.A048

def cited : List Fact := [
  ⟨247, .webSearch, 1427134490369135, 1, 146, 125⟩ ]

def claim : Claim := Sets.searched 247

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A048

#print axioms Cert.A048.verified
