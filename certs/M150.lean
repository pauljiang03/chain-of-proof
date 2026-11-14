import ChainOfProof
open ChainOfProof

namespace Cert.M150

def cited : List Fact := [
  ⟨199, .fileDeleted, 1427227902836000, 1, 114, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 199

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M150

#print axioms Cert.M150.verified
