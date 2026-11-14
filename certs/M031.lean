import ChainOfProof
open ChainOfProof

namespace Cert.M031

def cited : List Fact := [
  ⟨49, .lnkTarget, 1427230050485174, 1, 23, 39⟩,
  ⟨491, .volumeSeen, 1427230050485174, 1, 252, 39⟩,
  ⟨492, .volumeSeen, 1427230870763657, 1, 252, 40⟩,
  ⟨498, .volumeOnDevice, 1794614400000000, 1, 249, 40⟩ ]

def claim : Claim := .both (Sets.openedFromRecorded 49 491) (.both (Sets.sameLabel 491 492) (Sets.recordedOnDevice 492 498))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M031

#print axioms Cert.M031.verified
