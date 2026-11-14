import ChainOfProof
open ChainOfProof

namespace Cert.A063

def cited : List Fact := [
  ⟨262, .webSearch, 1427143432477705, 1, 145, 126⟩ ]

def claim : Claim := Sets.searched 262

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A063

#print axioms Cert.A063.verified
