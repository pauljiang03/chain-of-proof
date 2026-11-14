import ChainOfProof
open ChainOfProof

namespace Cert.A160

def cited : List Fact := [
  ⟨197, .fileDeleted, 1427226707133000, 1, 112, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A160

#print axioms Cert.A160.verified
