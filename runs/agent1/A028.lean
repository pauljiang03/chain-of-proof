import ChainOfProof
open ChainOfProof

namespace Cert.A028

def cited : List Fact := [
  ⟨126, .webSearch, 1427133873578434, 1, 76, 69⟩ ]

def claim : Claim := Sets.searched 126

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A028

#print axioms Cert.A028.verified
