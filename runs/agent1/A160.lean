import ChainOfProof
open ChainOfProof

namespace Cert.A160

def cited : List Fact := [
  ⟨147, .webSearch, 1427134400892344, 1, 87, 70⟩,
  ⟨218, .tag, 1794614400000000, 1, 87, 117⟩ ]

def claim : Claim := Sets.tagged 147 .obj 218 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A160

#print axioms Cert.A160.verified
