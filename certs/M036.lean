import ChainOfProof
open ChainOfProof

namespace Cert.M036

def cited : List Fact := [
  ⟨54, .lnkTarget, 1427230874336063, 1, 23, 40⟩,
  ⟨498, .volumeOnDevice, 1794614400000000, 1, 249, 40⟩ ]

def claim : Claim := Sets.openedFromDevice 54 498

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M036

#print axioms Cert.M036.verified
