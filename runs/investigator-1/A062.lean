import ChainOfProof
open ChainOfProof

namespace Cert.A062

def cited : List Fact := [
  ⟨12686, .fileContent, 1794614400000000, 1, 51, 16122⟩,
  ⟨12714, .fileContent, 1794614400000000, 1, 93, 16122⟩,
  ⟨12687, .fileContent, 1794614400000000, 1, 52, 16123⟩,
  ⟨12713, .fileContent, 1794614400000000, 1, 92, 16123⟩,
  ⟨12688, .fileContent, 1794614400000000, 1, 53, 16124⟩,
  ⟨12722, .fileContent, 1794614400000000, 1, 101, 16124⟩,
  ⟨12689, .fileContent, 1794614400000000, 1, 18, 16125⟩,
  ⟨12723, .fileContent, 1794614400000000, 1, 102, 16125⟩ ]

def claim : Claim := .both (Sets.sameContent 12686 12714) (.both (Sets.sameContent 12687 12713) (.both (Sets.sameContent 12688 12722) (Sets.sameContent 12689 12723)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A062

#print axioms Cert.A062.verified
