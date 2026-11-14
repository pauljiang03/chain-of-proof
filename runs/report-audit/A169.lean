import ChainOfProof
open ChainOfProof

namespace Cert.A169

def cited : List Fact := [
  ⟨206, .fileDeleted, 1427227902851000, 1, 121, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 206

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A169

#print axioms Cert.A169.verified
