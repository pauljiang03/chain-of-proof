import ChainOfProof
open ChainOfProof

namespace Cert.A022

def cited : List Fact := [
  ⟨221, .webSearch, 1427133820424839, 1, 132, 125⟩ ]

def claim : Claim := Sets.searched 221

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A022

#print axioms Cert.A022.verified
