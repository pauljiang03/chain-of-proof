import ChainOfProof
open ChainOfProof

namespace Cert.A016

def cited : List Fact := [
  ⟨44, .lnkTarget, 1427229853752619, 1, 34, 35⟩,
  ⟨368, .volumeSeen, 1427229853752619, 1, 204, 35⟩ ]

def claim : Claim := Sets.openedFromRecorded 44 368

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A016

#print axioms Cert.A016.verified
