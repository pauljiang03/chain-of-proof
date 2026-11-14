import ChainOfProof
open ChainOfProof

namespace Cert.M346

def cited : List Fact := [
  ⟨12700, .fileContent, 1794614400000000, 1, 62, 16133⟩,
  ⟨12706, .fileContent, 1794614400000000, 1, 56, 16133⟩,
  ⟨12711, .fileContent, 1794614400000000, 1, 65, 16133⟩ ]

def claim : Claim := .both (Sets.sameContent 12700 12706) (Sets.sameContent 12706 12711)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M346

#print axioms Cert.M346.verified
