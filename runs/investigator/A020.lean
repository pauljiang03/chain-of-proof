import ChainOfProof
open ChainOfProof

namespace Cert.A020

def cited : List Fact := [
  ⟨219, .webSearch, 1427133797161615, 1, 131, 125⟩ ]

def claim : Claim := Sets.searched 219

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A020

#print axioms Cert.A020.verified
