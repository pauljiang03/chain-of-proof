import ChainOfProof
open ChainOfProof

namespace Cert.A057

def cited : List Fact := [
  ⟨44, .lnkTarget, 1427229853752619, 1, 34, 35⟩,
  ⟨490, .volumeSeen, 1427229853752619, 1, 252, 35⟩,
  ⟨49, .lnkTarget, 1427230050485174, 1, 23, 39⟩,
  ⟨491, .volumeSeen, 1427230050485174, 1, 252, 39⟩,
  ⟨51, .lnkTarget, 1427230870904057, 1, 41, 40⟩,
  ⟨498, .volumeOnDevice, 1794614400000000, 1, 249, 40⟩,
  ⟨52, .lnkTarget, 1427230872900860, 1, 42, 40⟩,
  ⟨53, .lnkTarget, 1427230874320463, 1, 43, 40⟩ ]

def claim : Claim := .both (Sets.openedFromRecorded 44 490) (.both (Sets.openedFromRecorded 49 491) (.both (Sets.openedFromDevice 51 498) (.both (Sets.openedFromDevice 52 498) (Sets.openedFromDevice 53 498))))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A057

#print axioms Cert.A057.verified
