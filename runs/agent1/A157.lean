import ChainOfProof
open ChainOfProof

namespace Cert.A157

def cited : List Fact := [
  ⟨143, .webSearch, 1427134203820419, 1, 83, 70⟩,
  ⟨201, .tag, 1794614400000000, 1, 83, 117⟩ ]

def claim : Claim := Sets.tagged 143 .obj 201 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A157

#print axioms Cert.A157.verified
