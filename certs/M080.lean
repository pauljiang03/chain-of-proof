import ChainOfProof
open ChainOfProof

namespace Cert.M080

def cited : List Fact := [
  ⟨66, .fileCreated, 1424037128960000, 10000, 22, 19⟩,
  ⟨158, .fileModified, 1417706690000000, 10000, 22, 19⟩,
  ⟨323, .tag, 1794614400000000, 1, 22, 197⟩ ]

def claim : Claim := .both (Sets.copiedHere 66 158) (Sets.tagged 66 .obj 323 197)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M080

#print axioms Cert.M080.verified
