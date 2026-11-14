import ChainOfProof
open ChainOfProof

namespace Cert.A121

def cited : List Fact := [
  ⟨24, .lnkTarget, 1427135874522916, 1, 20, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 24 374

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A121

#print axioms Cert.A121.verified
