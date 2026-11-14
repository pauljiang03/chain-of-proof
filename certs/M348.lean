import ChainOfProof
open ChainOfProof

namespace Cert.M348

def cited : List Fact := [
  ⟨12716, .fileContent, 1794614400000000, 1, 95, 16141⟩,
  ⟨12758, .fileContent, 1794614400000000, 1, 116, 16141⟩,
  ⟨12762, .fileContent, 1794614400000000, 1, 117, 16141⟩ ]

def claim : Claim := .both (Sets.sameContent 12716 12758) (Sets.sameContent 12758 12762)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M348

#print axioms Cert.M348.verified
