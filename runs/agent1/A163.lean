import ChainOfProof
open ChainOfProof

namespace Cert.A163

def cited : List Fact := [
  ⟨151, .webSearch, 1427134490369135, 1, 90, 69⟩,
  ⟨220, .tag, 1794614400000000, 1, 90, 117⟩ ]

def claim : Claim := Sets.tagged 151 .obj 220 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A163

#print axioms Cert.A163.verified
