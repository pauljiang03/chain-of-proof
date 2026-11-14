import ChainOfProof
open ChainOfProof

namespace Cert.A166

def cited : List Fact := [
  ⟨203, .fileDeleted, 1427227902851000, 1, 118, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 203

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A166

#print axioms Cert.A166.verified
