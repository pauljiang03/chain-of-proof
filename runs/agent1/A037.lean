import ChainOfProof
open ChainOfProof

namespace Cert.A037

def cited : List Fact := [
  ⟨135, .webSearch, 1427134074991194, 1, 79, 70⟩ ]

def claim : Claim := Sets.searched 135

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A037

#print axioms Cert.A037.verified
