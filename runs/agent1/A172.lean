import ChainOfProof
open ChainOfProof

namespace Cert.A172

def cited : List Fact := [
  ⟨197, .webSearch, 1427294871248203, 1, 114, 70⟩,
  ⟨217, .tag, 1794614400000000, 1, 114, 117⟩ ]

def claim : Claim := Sets.tagged 197 .obj 217 117

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A172

#print axioms Cert.A172.verified
