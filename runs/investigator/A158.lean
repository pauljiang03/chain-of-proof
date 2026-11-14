import ChainOfProof
open ChainOfProof

namespace Cert.A158

def cited : List Fact := [
  ⟨49, .lnkTarget, 1427230050485174, 1, 23, 39⟩,
  ⟨369, .volumeSeen, 1427230050485174, 1, 204, 39⟩ ]

def claim : Claim := Sets.openedFromRecorded 49 369

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A158

#print axioms Cert.A158.verified
