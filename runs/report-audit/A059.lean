import ChainOfProof
open ChainOfProof

namespace Cert.A059

def cited : List Fact := [
  ⟨159, .fileModified, 1418746226000000, 10000, 51, 19⟩,
  ⟨325, .tag, 1794614400000000, 1, 51, 198⟩ ]

def claim : Claim := Sets.tagged 159 .obj 325 198

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A059

#print axioms Cert.A059.verified
