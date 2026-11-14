import ChainOfProof
open ChainOfProof

namespace Cert.M030

def cited : List Fact := [
  ⟨48, .lnkTarget, 1427229858901833, 1, 34, 35⟩,
  ⟨490, .volumeSeen, 1427229853752619, 1, 252, 35⟩,
  ⟨431, .tag, 1794614400000000, 1, 34, 232⟩,
  ⟨492, .volumeSeen, 1427230870763657, 1, 252, 40⟩,
  ⟨498, .volumeOnDevice, 1794614400000000, 1, 249, 40⟩ ]

def claim : Claim := .both (Sets.openedFromRecorded 48 490) (.both (Sets.tagged 48 .obj 431 232) (.both (Sets.sameLabel 490 492) (Sets.recordedOnDevice 492 498)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M030

#print axioms Cert.M030.verified
