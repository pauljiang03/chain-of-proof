import ChainOfProof
open ChainOfProof

namespace Cert.M350

def cited : List Fact := [
  ⟨12718, .fileContent, 1794614400000000, 1, 97, 16143⟩,
  ⟨12760, .fileContent, 1794614400000000, 1, 120, 16143⟩,
  ⟨12764, .fileContent, 1794614400000000, 1, 121, 16143⟩ ]

def claim : Claim := .both (Sets.sameContent 12718 12760) (Sets.sameContent 12760 12764)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M350

#print axioms Cert.M350.verified
