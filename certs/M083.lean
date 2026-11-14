import ChainOfProof
open ChainOfProof

namespace Cert.M083

def cited : List Fact := [
  ⟨69, .fileCreated, 1424037132550000, 10000, 53, 19⟩,
  ⟨209, .fileModified, 1418939458000000, 10000, 53, 19⟩,
  ⟨403, .tag, 1794614400000000, 1, 53, 231⟩,
  ⟨404, .tag, 1794614400000000, 1, 53, 234⟩ ]

def claim : Claim := .both (Sets.copiedHere 69 209) (.both (Sets.tagged 69 .obj 403 231) (Sets.tagged 69 .obj 404 234))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M083

#print axioms Cert.M083.verified
