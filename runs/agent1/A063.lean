import ChainOfProof
open ChainOfProof

namespace Cert.A063

def cited : List Fact := [
  ⟨161, .webSearch, 1427140063009623, 1, 96, 69⟩ ]

def claim : Claim := Sets.searched 161

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A063

#print axioms Cert.A063.verified
