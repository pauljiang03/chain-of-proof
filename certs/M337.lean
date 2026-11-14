import ChainOfProof
open ChainOfProof

namespace Cert.M337

def cited : List Fact := [
  ⟨12686, .fileContent, 1794614400000000, 1, 51, 16122⟩,
  ⟨12714, .fileContent, 1794614400000000, 1, 93, 16122⟩,
  ⟨12754, .fileContent, 1794614400000000, 1, 34, 16122⟩,
  ⟨12756, .fileContent, 1794614400000000, 1, 113, 16122⟩ ]

def claim : Claim := .both (Sets.sameContent 12686 12714) (.both (Sets.sameContent 12714 12754) (Sets.sameContent 12754 12756))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M337

#print axioms Cert.M337.verified
