import ChainOfProof
open ChainOfProof

namespace Cert.A170

def cited : List Fact := [
  ⟨207, .fileDeleted, 1427227902851000, 1, 122, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 207

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A170

#print axioms Cert.A170.verified
