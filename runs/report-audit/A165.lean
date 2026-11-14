import ChainOfProof
open ChainOfProof

namespace Cert.A165

def cited : List Fact := [
  ⟨202, .fileDeleted, 1427227902851000, 1, 117, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 202

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A165

#print axioms Cert.A165.verified
