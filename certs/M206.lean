import ChainOfProof
open ChainOfProof

namespace Cert.M206

def cited : List Fact := [
  ⟨279, .fileDeleted, 1427227902851000, 1, 154, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 279

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M206

#print axioms Cert.M206.verified
