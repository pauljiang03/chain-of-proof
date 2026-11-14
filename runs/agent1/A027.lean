import ChainOfProof
open ChainOfProof

namespace Cert.A027

def cited : List Fact := [
  ⟨125, .webSearch, 1427133820424839, 1, 76, 69⟩ ]

def claim : Claim := Sets.searched 125

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A027

#print axioms Cert.A027.verified
