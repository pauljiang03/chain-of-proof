import ChainOfProof
open ChainOfProof

namespace Cert.A106

def cited : List Fact := [
  ⟨28, .lnkTarget, 1427135901230162, 1, 22, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 28 241

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A106

#print axioms Cert.A106.verified
