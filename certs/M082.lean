import ChainOfProof
open ChainOfProof

namespace Cert.M082

def cited : List Fact := [
  ⟨68, .fileCreated, 1424037130630000, 10000, 52, 19⟩,
  ⟨250, .fileModified, 1422046030000000, 10000, 52, 19⟩,
  ⟨400, .tag, 1794614400000000, 1, 52, 231⟩,
  ⟨401, .tag, 1794614400000000, 1, 52, 233⟩ ]

def claim : Claim := .both (Sets.copiedHere 68 250) (.both (Sets.tagged 68 .obj 400 231) (Sets.tagged 68 .obj 401 233))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M082

#print axioms Cert.M082.verified
