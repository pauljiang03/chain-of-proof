import ChainOfProof
open ChainOfProof

namespace Cert.A109

def cited : List Fact := [
  ⟨250, .webSearch, 1427134634631105, 1, 149, 125⟩ ]

def claim : Claim := Sets.searched 250

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A109

#print axioms Cert.A109.verified
