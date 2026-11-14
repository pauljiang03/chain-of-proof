import ChainOfProof
open ChainOfProof

namespace Cert.M358

def cited : List Fact := [
  ⟨12728, .fileContent, 1794614400000000, 1, 107, 16151⟩,
  ⟨12779, .fileContent, 1794614400000000, 1, 140, 16151⟩,
  ⟨12785, .fileContent, 1794614400000000, 1, 141, 16151⟩ ]

def claim : Claim := .both (Sets.sameContent 12728 12779) (Sets.sameContent 12779 12785)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M358

#print axioms Cert.M358.verified
