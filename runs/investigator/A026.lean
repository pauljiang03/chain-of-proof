import ChainOfProof
open ChainOfProof

namespace Cert.A026

def cited : List Fact := [
  ⟨225, .webSearch, 1427133919638342, 1, 132, 125⟩ ]

def claim : Claim := Sets.searched 225

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A026

#print axioms Cert.A026.verified
