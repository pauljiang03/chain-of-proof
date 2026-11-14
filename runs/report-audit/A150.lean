import ChainOfProof
open ChainOfProof

namespace Cert.A150

def cited : List Fact := [
  ⟨161, .fileModified, 1418939458000000, 10000, 53, 19⟩,
  ⟨330, .tag, 1794614400000000, 1, 53, 200⟩ ]

def claim : Claim := Sets.tagged 161 .obj 330 200

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A150

#print axioms Cert.A150.verified
