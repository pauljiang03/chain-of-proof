import ChainOfProof
open ChainOfProof

namespace Cert.A110

def cited : List Fact := [
  ⟨251, .webSearch, 1427134690237438, 1, 150, 125⟩ ]

def claim : Claim := Sets.searched 251

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A110

#print axioms Cert.A110.verified
