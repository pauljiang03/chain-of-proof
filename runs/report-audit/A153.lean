import ChainOfProof
open ChainOfProof

namespace Cert.A153

def cited : List Fact := [
  ⟨164, .fileModified, 1419018826000000, 2000000, 102, 69⟩,
  ⟨342, .tag, 1794614400000000, 1, 102, 201⟩ ]

def claim : Claim := Sets.tagged 164 .obj 342 201

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A153

#print axioms Cert.A153.verified
