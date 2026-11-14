import ChainOfProof
open ChainOfProof

namespace Cert.M082

def cited : List Fact := [
  ⟨68, .fileCreated, 1424037130630000, 10000, 52, 19⟩,
  ⟨96, .fileModified, 1422046030000000, 10000, 52, 19⟩,
  ⟨205, .tag, 1794614400000000, 1, 52, 118⟩ ]

def claim : Claim := .both (Sets.copiedHere 68 96) (Sets.tagged 68 .obj 205 118)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M082

#print axioms Cert.M082.verified
