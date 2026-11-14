import ChainOfProof
open ChainOfProof

namespace Cert.M155

def cited : List Fact := [
  ⟨204, .fileDeleted, 1427227902851000, 1, 119, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 204

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M155

#print axioms Cert.M155.verified
