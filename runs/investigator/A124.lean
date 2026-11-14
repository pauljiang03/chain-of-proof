import ChainOfProof
open ChainOfProof

namespace Cert.A124

def cited : List Fact := [
  ⟨28, .lnkTarget, 1427135901230162, 1, 22, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 28 374

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A124

#print axioms Cert.A124.verified
