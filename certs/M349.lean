import ChainOfProof
open ChainOfProof

namespace Cert.M349

def cited : List Fact := [
  ⟨12717, .fileContent, 1794614400000000, 1, 96, 16142⟩,
  ⟨12759, .fileContent, 1794614400000000, 1, 118, 16142⟩,
  ⟨12763, .fileContent, 1794614400000000, 1, 119, 16142⟩ ]

def claim : Claim := .both (Sets.sameContent 12717 12759) (Sets.sameContent 12759 12763)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M349

#print axioms Cert.M349.verified
