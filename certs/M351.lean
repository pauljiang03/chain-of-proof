import ChainOfProof
open ChainOfProof

namespace Cert.M351

def cited : List Fact := [
  ⟨12719, .fileContent, 1794614400000000, 1, 98, 16144⟩,
  ⟨12765, .fileContent, 1794614400000000, 1, 122, 16144⟩,
  ⟨12768, .fileContent, 1794614400000000, 1, 123, 16144⟩ ]

def claim : Claim := .both (Sets.sameContent 12719 12765) (Sets.sameContent 12765 12768)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M351

#print axioms Cert.M351.verified
