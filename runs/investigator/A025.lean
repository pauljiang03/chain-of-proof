import ChainOfProof
open ChainOfProof

namespace Cert.A025

def cited : List Fact := [
  ⟨224, .webSearch, 1427133918131407, 1, 132, 125⟩ ]

def claim : Claim := Sets.searched 224

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A025

#print axioms Cert.A025.verified
