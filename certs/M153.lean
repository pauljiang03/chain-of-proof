import ChainOfProof
open ChainOfProof

namespace Cert.M153

def cited : List Fact := [
  ⟨202, .fileDeleted, 1427227902851000, 1, 117, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 202

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M153

#print axioms Cert.M153.verified
