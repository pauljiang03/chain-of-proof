import ChainOfProof
open ChainOfProof

namespace Cert.A164

def cited : List Fact := [
  ⟨201, .fileDeleted, 1427227902851000, 1, 116, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 201

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A164

#print axioms Cert.A164.verified
