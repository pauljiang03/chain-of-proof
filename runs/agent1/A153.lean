import ChainOfProof
open ChainOfProof

namespace Cert.A153

def cited : List Fact := [
  ⟨131, .webSearch, 1427133948655159, 1, 77, 69⟩,
  ⟨231, .tag, 1794614400000000, 1, 77, 117⟩ ]

def claim : Claim := Sets.tagged 131 .obj 231 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A153

#print axioms Cert.A153.verified
