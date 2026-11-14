import ChainOfProof
open ChainOfProof

namespace Cert.A024

def cited : List Fact := [
  ⟨223, .webSearch, 1427133915865196, 1, 132, 125⟩ ]

def claim : Claim := Sets.searched 223

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A024

#print axioms Cert.A024.verified
