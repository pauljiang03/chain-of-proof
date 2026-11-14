import ChainOfProof
open ChainOfProof

namespace Cert.A086

def cited : List Fact := [
  ⟨285, .webSearch, 1427144158732159, 1, 166, 126⟩ ]

def claim : Claim := Sets.searched 285

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A086

#print axioms Cert.A086.verified
