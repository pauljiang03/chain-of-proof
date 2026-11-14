import ChainOfProof
open ChainOfProof

namespace Cert.A104

def cited : List Fact := [
  ⟨26, .lnkTarget, 1427135901167763, 1, 22, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 26 241

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A104

#print axioms Cert.A104.verified
