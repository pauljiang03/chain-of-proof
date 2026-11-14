import ChainOfProof
open ChainOfProof

namespace Cert.A102

def cited : List Fact := [
  ⟨44, .lnkTarget, 1427229853752619, 1, 34, 35⟩,
  ⟨368, .volumeSeen, 1427229853752619, 1, 204, 35⟩,
  ⟨49, .lnkTarget, 1427230050485174, 1, 23, 39⟩,
  ⟨369, .volumeSeen, 1427230050485174, 1, 204, 39⟩,
  ⟨50, .lnkTarget, 1427230870763657, 1, 23, 40⟩,
  ⟨370, .volumeSeen, 1427230870763657, 1, 204, 40⟩ ]

def claim : Claim := .both (Sets.openedFromRecorded 44 368) (.both (Sets.openedFromRecorded 49 369) (Sets.openedFromRecorded 50 370))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A102

#print axioms Cert.A102.verified
