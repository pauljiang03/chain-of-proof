import ChainOfProof
open ChainOfProof

namespace Cert.A077

def cited : List Fact := [
  ⟨276, .webSearch, 1427144118340597, 1, 162, 126⟩ ]

def claim : Claim := Sets.searched 276

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A077

#print axioms Cert.A077.verified
