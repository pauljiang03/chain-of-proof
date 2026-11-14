import ChainOfProof
open ChainOfProof

namespace Cert.M156

def cited : List Fact := [
  ⟨205, .fileDeleted, 1427227902851000, 1, 120, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 205

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M156

#print axioms Cert.M156.verified
