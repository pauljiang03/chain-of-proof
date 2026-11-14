import ChainOfProof
open ChainOfProof

namespace Cert.A093

def cited : List Fact := [
  ⟨290, .webSearch, 1427294804752905, 1, 168, 126⟩,
  ⟨292, .webSearch, 1427294814471205, 1, 169, 126⟩,
  ⟨293, .webSearch, 1427294871248203, 1, 170, 126⟩ ]

def claim : Claim := .both (Sets.searched 290) (.both (Sets.searched 292) (Sets.searched 293))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A093

#print axioms Cert.A093.verified
