import ChainOfProof
open ChainOfProof

namespace Cert.M199

def cited : List Fact := [
  ⟨272, .fileDeleted, 1427226707149000, 1, 147, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 272

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M199

#print axioms Cert.M199.verified
