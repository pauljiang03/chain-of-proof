import ChainOfProof
open ChainOfProof

namespace Cert.M202

def cited : List Fact := [
  ⟨275, .fileDeleted, 1427227902851000, 1, 150, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 275

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M202

#print axioms Cert.M202.verified
