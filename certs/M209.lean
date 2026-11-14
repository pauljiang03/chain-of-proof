import ChainOfProof
open ChainOfProof

namespace Cert.M209

def cited : List Fact := [
  ⟨282, .fileDeleted, 1427227902851000, 1, 157, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 282

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M209

#print axioms Cert.M209.verified
