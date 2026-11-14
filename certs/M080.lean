import ChainOfProof
open ChainOfProof

namespace Cert.M080

def cited : List Fact := [
  ⟨66, .fileCreated, 1424037128960000, 10000, 22, 19⟩,
  ⟨202, .fileModified, 1417706690000000, 10000, 22, 19⟩,
  ⟨397, .tag, 1794614400000000, 1, 22, 231⟩ ]

def claim : Claim := .both (Sets.copiedHere 66 202) (Sets.tagged 66 .obj 397 231)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M080

#print axioms Cert.M080.verified
