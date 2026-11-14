import ChainOfProof
open ChainOfProof

namespace Cert.M201

def cited : List Fact := [
  ⟨274, .fileDeleted, 1427227902836000, 1, 149, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 274

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M201

#print axioms Cert.M201.verified
