import ChainOfProof
open ChainOfProof

namespace Cert.M033

def cited : List Fact := [
  ⟨51, .lnkTarget, 1427230870904057, 1, 41, 40⟩,
  ⟨498, .volumeOnDevice, 1794614400000000, 1, 249, 40⟩ ]

def claim : Claim := Sets.openedFromDevice 51 498

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M033

#print axioms Cert.M033.verified
