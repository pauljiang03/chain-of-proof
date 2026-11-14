import ChainOfProof
open ChainOfProof

namespace Cert.M159

def cited : List Fact := [
  ⟨208, .fileDeleted, 1427227902851000, 1, 123, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 208

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M159

#print axioms Cert.M159.verified
