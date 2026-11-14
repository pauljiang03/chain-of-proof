import ChainOfProof
open ChainOfProof

namespace Cert.M200

def cited : List Fact := [
  ⟨273, .fileDeleted, 1427227902836000, 1, 148, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 273

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M200

#print axioms Cert.M200.verified
