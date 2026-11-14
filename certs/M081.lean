import ChainOfProof
open ChainOfProof

namespace Cert.M081

def cited : List Fact := [
  ⟨67, .fileCreated, 1424037129290000, 10000, 51, 19⟩,
  ⟨159, .fileModified, 1418746226000000, 10000, 51, 19⟩,
  ⟨324, .tag, 1794614400000000, 1, 51, 197⟩,
  ⟨325, .tag, 1794614400000000, 1, 51, 198⟩ ]

def claim : Claim := .both (Sets.copiedHere 67 159) (.both (Sets.tagged 67 .obj 324 197) (Sets.tagged 67 .obj 325 198))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M081

#print axioms Cert.M081.verified
