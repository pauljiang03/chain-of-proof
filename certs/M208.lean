import ChainOfProof
open ChainOfProof

namespace Cert.M208

def cited : List Fact := [
  ⟨281, .fileDeleted, 1427227902851000, 1, 156, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 281

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M208

#print axioms Cert.M208.verified
