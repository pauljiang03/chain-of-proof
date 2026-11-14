import ChainOfProof
open ChainOfProof

namespace Cert.A063

def cited : List Fact := [
  ⟨12686, .fileContent, 1794614400000000, 1, 51, 16122⟩,
  ⟨12754, .fileContent, 1794614400000000, 1, 34, 16122⟩,
  ⟨12687, .fileContent, 1794614400000000, 1, 52, 16123⟩,
  ⟨12753, .fileContent, 1794614400000000, 1, 110, 16123⟩,
  ⟨12688, .fileContent, 1794614400000000, 1, 53, 16124⟩,
  ⟨12771, .fileContent, 1794614400000000, 1, 128, 16124⟩,
  ⟨12689, .fileContent, 1794614400000000, 1, 18, 16125⟩,
  ⟨12772, .fileContent, 1794614400000000, 1, 130, 16125⟩ ]

def claim : Claim := .both (Sets.sameContent 12686 12754) (.both (Sets.sameContent 12687 12753) (.both (Sets.sameContent 12688 12771) (Sets.sameContent 12689 12772)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A063

#print axioms Cert.A063.verified
