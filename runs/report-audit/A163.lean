import ChainOfProof
open ChainOfProof

namespace Cert.A163

def cited : List Fact := [
  ⟨200, .fileDeleted, 1427227902836000, 1, 115, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 200

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A163

#print axioms Cert.A163.verified
