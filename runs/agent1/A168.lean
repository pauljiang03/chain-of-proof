import ChainOfProof
open ChainOfProof

namespace Cert.A168

def cited : List Fact := [
  ⟨157, .webSearch, 1427134710872763, 1, 95, 69⟩,
  ⟨229, .tag, 1794614400000000, 1, 95, 117⟩ ]

def claim : Claim := Sets.tagged 157 .obj 229 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A168

#print axioms Cert.A168.verified
