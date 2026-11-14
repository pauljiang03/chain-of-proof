import ChainOfProof
open ChainOfProof

namespace Cert.A159

def cited : List Fact := [
  ⟨196, .fileDeleted, 1427226707133000, 1, 111, 4⟩ ]

def claim : Claim := Sets.fileDeletedAt 196

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A159

#print axioms Cert.A159.verified
