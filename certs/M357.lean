import ChainOfProof
open ChainOfProof

namespace Cert.M357

def cited : List Fact := [
  ⟨12727, .fileContent, 1794614400000000, 1, 106, 16150⟩,
  ⟨12778, .fileContent, 1794614400000000, 1, 138, 16150⟩,
  ⟨12784, .fileContent, 1794614400000000, 1, 139, 16150⟩ ]

def claim : Claim := .both (Sets.sameContent 12727 12778) (Sets.sameContent 12778 12784)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M357

#print axioms Cert.M357.verified
