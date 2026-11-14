import ChainOfProof
open ChainOfProof

namespace Cert.M207

def cited : List Fact := [
  ⟨280, .fileDeleted, 1427227902851000, 1, 155, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 280

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M207

#print axioms Cert.M207.verified
