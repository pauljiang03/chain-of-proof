import ChainOfProof
open ChainOfProof

namespace Cert.M154

def cited : List Fact := [
  ⟨203, .fileDeleted, 1427227902851000, 1, 118, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 203

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M154

#print axioms Cert.M154.verified
