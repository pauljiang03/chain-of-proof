import ChainOfProof
open ChainOfProof

namespace Cert.A170

def cited : List Fact := [
  ⟨194, .webSearch, 1427294804752905, 1, 112, 70⟩,
  ⟨215, .tag, 1794614400000000, 1, 112, 117⟩ ]

def claim : Claim := Sets.tagged 194 .obj 215 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A170

#print axioms Cert.A170.verified
