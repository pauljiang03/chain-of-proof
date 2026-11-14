import ChainOfProof
open ChainOfProof

namespace Cert.A021

def cited : List Fact := [
  ⟨220, .webSearch, 1427133811261408, 1, 131, 125⟩ ]

def claim : Claim := Sets.searched 220

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A021

#print axioms Cert.A021.verified
