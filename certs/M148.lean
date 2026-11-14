import ChainOfProof
open ChainOfProof

namespace Cert.M148

def cited : List Fact := [
  ⟨197, .fileDeleted, 1427226707133000, 1, 112, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M148

#print axioms Cert.M148.verified
