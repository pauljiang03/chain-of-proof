import ChainOfProof
open ChainOfProof

namespace Cert.M203

def cited : List Fact := [
  ⟨276, .fileDeleted, 1427227902851000, 1, 151, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 276

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M203

#print axioms Cert.M203.verified
