import ChainOfProof
open ChainOfProof

namespace Cert.A167

def cited : List Fact := [
  ⟨204, .fileDeleted, 1427227902851000, 1, 119, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 204

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A167

#print axioms Cert.A167.verified
