import ChainOfProof
open ChainOfProof

namespace Cert.A100

def cited : List Fact := [
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 21 241

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A100

#print axioms Cert.A100.verified
