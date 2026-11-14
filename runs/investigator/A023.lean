import ChainOfProof
open ChainOfProof

namespace Cert.A023

def cited : List Fact := [
  ⟨222, .webSearch, 1427133873578434, 1, 132, 125⟩ ]

def claim : Claim := Sets.searched 222

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A023

#print axioms Cert.A023.verified
