import ChainOfProof
open ChainOfProof

namespace Cert.A161

def cited : List Fact := [
  ⟨148, .webSearch, 1427134417494371, 1, 88, 70⟩,
  ⟨219, .tag, 1794614400000000, 1, 88, 117⟩ ]

def claim : Claim := Sets.tagged 148 .obj 219 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A161

#print axioms Cert.A161.verified
