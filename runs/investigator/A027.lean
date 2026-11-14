import ChainOfProof
open ChainOfProof

namespace Cert.A027

def cited : List Fact := [
  ⟨226, .webSearch, 1427133922229486, 1, 132, 125⟩ ]

def claim : Claim := Sets.searched 226

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A027

#print axioms Cert.A027.verified
