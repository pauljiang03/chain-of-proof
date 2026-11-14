import ChainOfProof
open ChainOfProof

namespace Cert.M345

def cited : List Fact := [
  ⟨12699, .fileContent, 1794614400000000, 1, 61, 16132⟩,
  ⟨12705, .fileContent, 1794614400000000, 1, 55, 16132⟩,
  ⟨12710, .fileContent, 1794614400000000, 1, 64, 16132⟩ ]

def claim : Claim := .both (Sets.sameContent 12699 12705) (Sets.sameContent 12705 12710)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M345

#print axioms Cert.M345.verified
