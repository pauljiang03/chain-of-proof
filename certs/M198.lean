import ChainOfProof
open ChainOfProof

namespace Cert.M198

def cited : List Fact := [
  ⟨271, .fileDeleted, 1427226707133000, 1, 146, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 271

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M198

#print axioms Cert.M198.verified
