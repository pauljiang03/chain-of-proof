import ChainOfProof
open ChainOfProof

namespace Cert.A044

def cited : List Fact := [
  ⟨48, .lnkTarget, 1427229858901833, 1, 34, 35⟩,
  ⟨368, .volumeSeen, 1427229853752619, 1, 204, 35⟩ ]

def claim : Claim := Sets.openedFromRecorded 48 368

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A044

#print axioms Cert.A044.verified
