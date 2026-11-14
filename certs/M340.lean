import ChainOfProof
open ChainOfProof

namespace Cert.M340

def cited : List Fact := [
  ⟨12689, .fileContent, 1794614400000000, 1, 18, 16125⟩,
  ⟨12723, .fileContent, 1794614400000000, 1, 102, 16125⟩,
  ⟨12772, .fileContent, 1794614400000000, 1, 130, 16125⟩,
  ⟨12774, .fileContent, 1794614400000000, 1, 131, 16125⟩ ]

def claim : Claim := .both (Sets.sameContent 12689 12723) (.both (Sets.sameContent 12723 12772) (Sets.sameContent 12772 12774))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M340

#print axioms Cert.M340.verified
