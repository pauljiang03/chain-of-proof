import ChainOfProof
open ChainOfProof

namespace Cert.A144

def cited : List Fact := [
  ⟨159, .fileModified, 1418746226000000, 10000, 51, 19⟩,
  ⟨324, .tag, 1794614400000000, 1, 51, 197⟩ ]

def claim : Claim := Sets.tagged 159 .obj 324 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A144

#print axioms Cert.A144.verified
