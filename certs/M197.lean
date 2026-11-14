import ChainOfProof
open ChainOfProof

namespace Cert.M197

def cited : List Fact := [
  ⟨270, .fileDeleted, 1427226707133000, 1, 145, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 270

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M197

#print axioms Cert.M197.verified
