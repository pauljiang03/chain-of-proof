import ChainOfProof
open ChainOfProof

namespace Cert.M035

def cited : List Fact := [
  ⟨53, .lnkTarget, 1427230874320463, 1, 43, 40⟩,
  ⟨498, .volumeOnDevice, 1794614400000000, 1, 249, 40⟩ ]

def claim : Claim := Sets.openedFromDevice 53 498

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M035

#print axioms Cert.M035.verified
