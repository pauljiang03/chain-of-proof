import ChainOfProof
open ChainOfProof

namespace Cert.M205

def cited : List Fact := [
  ⟨278, .fileDeleted, 1427227902851000, 1, 153, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 278

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M205

#print axioms Cert.M205.verified
