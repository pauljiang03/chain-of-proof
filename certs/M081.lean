import ChainOfProof
open ChainOfProof

namespace Cert.M081

def cited : List Fact := [
  ⟨67, .fileCreated, 1424037129290000, 10000, 51, 19⟩,
  ⟨205, .fileModified, 1418746226000000, 10000, 51, 19⟩,
  ⟨398, .tag, 1794614400000000, 1, 51, 231⟩,
  ⟨399, .tag, 1794614400000000, 1, 51, 232⟩ ]

def claim : Claim := .both (Sets.copiedHere 67 205) (.both (Sets.tagged 67 .obj 398 231) (Sets.tagged 67 .obj 399 232))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M081

#print axioms Cert.M081.verified
