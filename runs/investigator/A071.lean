import ChainOfProof
open ChainOfProof

namespace Cert.A071

def cited : List Fact := [
  ⟨270, .webSearch, 1427144108553579, 1, 159, 126⟩ ]

def claim : Claim := Sets.searched 270

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A071

#print axioms Cert.A071.verified
