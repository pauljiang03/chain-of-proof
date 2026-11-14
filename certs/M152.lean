import ChainOfProof
open ChainOfProof

namespace Cert.M152

def cited : List Fact := [
  ⟨201, .fileDeleted, 1427227902851000, 1, 116, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 201

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M152

#print axioms Cert.M152.verified
