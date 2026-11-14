import ChainOfProof
open ChainOfProof

namespace Cert.A054

def cited : List Fact := [
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩,
  ⟨496, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩,
  ⟨405, .tag, 1794614400000000, 1, 18, 231⟩,
  ⟨26, .lnkTarget, 1427135901167763, 1, 22, 19⟩,
  ⟨397, .tag, 1794614400000000, 1, 22, 231⟩ ]

def claim : Claim := .both (Sets.openedFromDevice 21 496) (.both (Sets.tagged 21 .obj 405 231) (.both (Sets.openedFromDevice 26 496) (Sets.tagged 26 .obj 397 231)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A054

#print axioms Cert.A054.verified
