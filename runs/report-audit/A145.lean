import ChainOfProof
open ChainOfProof

namespace Cert.A145

def cited : List Fact := [
  ⟨177, .fileModified, 1422046030000000, 2000000, 92, 69⟩,
  ⟨339, .tag, 1794614400000000, 1, 92, 199⟩ ]

def claim : Claim := Sets.tagged 177 .obj 339 199

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A145

#print axioms Cert.A145.verified
