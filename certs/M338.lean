import ChainOfProof
open ChainOfProof

namespace Cert.M338

def cited : List Fact := [
  ⟨12687, .fileContent, 1794614400000000, 1, 52, 16123⟩,
  ⟨12713, .fileContent, 1794614400000000, 1, 92, 16123⟩,
  ⟨12753, .fileContent, 1794614400000000, 1, 110, 16123⟩,
  ⟨12755, .fileContent, 1794614400000000, 1, 112, 16123⟩ ]

def claim : Claim := .both (Sets.sameContent 12687 12713) (.both (Sets.sameContent 12713 12753) (Sets.sameContent 12753 12755))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M338

#print axioms Cert.M338.verified
