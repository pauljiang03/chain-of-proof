import ChainOfProof
open ChainOfProof

namespace Cert.A158

def cited : List Fact := [
  ⟨195, .fileDeleted, 1427226707117000, 1, 110, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 195

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A158

#print axioms Cert.A158.verified
