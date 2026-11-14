import ChainOfProof
open ChainOfProof

namespace Cert.A029

def cited : List Fact := [
  ⟨26, .lnkTarget, 1427135901167763, 1, 22, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 26 374

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A029

#print axioms Cert.A029.verified
