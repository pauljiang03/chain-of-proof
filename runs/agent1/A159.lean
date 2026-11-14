import ChainOfProof
open ChainOfProof

namespace Cert.A159

def cited : List Fact := [
  ⟨146, .webSearch, 1427134355567263, 1, 86, 70⟩,
  ⟨235, .tag, 1794614400000000, 1, 86, 117⟩ ]

def claim : Claim := Sets.tagged 146 .obj 235 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A159

#print axioms Cert.A159.verified
