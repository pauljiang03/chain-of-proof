import ChainOfProof
open ChainOfProof

namespace Cert.A026

def cited : List Fact := [
  ⟨124, .webSearch, 1427133811261408, 1, 75, 69⟩ ]

def claim : Claim := Sets.searched 124

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A026

#print axioms Cert.A026.verified
