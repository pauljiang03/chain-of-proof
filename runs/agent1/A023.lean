import ChainOfProof
open ChainOfProof

namespace Cert.A023

def cited : List Fact := [
  ⟨121, .webSearch, 1427133729303892, 1, 74, 69⟩ ]

def claim : Claim := Sets.searched 121

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A023

#print axioms Cert.A023.verified
