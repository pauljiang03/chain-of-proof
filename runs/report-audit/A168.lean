import ChainOfProof
open ChainOfProof

namespace Cert.A168

def cited : List Fact := [
  ⟨205, .fileDeleted, 1427227902851000, 1, 120, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 205

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A168

#print axioms Cert.A168.verified
