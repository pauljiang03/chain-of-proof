import ChainOfProof
open ChainOfProof

namespace Cert.A149

def cited : List Fact := [
  ⟨162, .fileModified, 1418939458000000, 2000000, 101, 69⟩,
  ⟨341, .tag, 1794614400000000, 1, 101, 200⟩ ]

def claim : Claim := Sets.tagged 162 .obj 341 200

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A149

#print axioms Cert.A149.verified
