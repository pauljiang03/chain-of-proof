import ChainOfProof
open ChainOfProof

namespace Cert.A158

def cited : List Fact := [
  ⟨145, .webSearch, 1427134310582693, 1, 85, 70⟩,
  ⟨232, .tag, 1794614400000000, 1, 85, 117⟩ ]

def claim : Claim := Sets.tagged 145 .obj 232 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A158

#print axioms Cert.A158.verified
