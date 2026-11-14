import ChainOfProof
open ChainOfProof

namespace Cert.A076

def cited : List Fact := [
  ⟨275, .webSearch, 1427144118330597, 1, 162, 126⟩ ]

def claim : Claim := Sets.searched 275

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A076

#print axioms Cert.A076.verified
