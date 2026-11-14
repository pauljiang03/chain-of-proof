import ChainOfProof
open ChainOfProof

namespace Cert.M157

def cited : List Fact := [
  ⟨206, .fileDeleted, 1427227902851000, 1, 121, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 206

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M157

#print axioms Cert.M157.verified
