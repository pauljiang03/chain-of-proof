import ChainOfProof
open ChainOfProof

namespace Cert.M149

def cited : List Fact := [
  ⟨198, .fileDeleted, 1427226707149000, 1, 113, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 198

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M149

#print axioms Cert.M149.verified
