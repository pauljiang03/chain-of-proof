import ChainOfProof
open ChainOfProof

namespace Cert.M032

def cited : List Fact := [
  ⟨50, .lnkTarget, 1427230870763657, 1, 23, 40⟩,
  ⟨498, .volumeOnDevice, 1794614400000000, 1, 249, 40⟩ ]

def claim : Claim := Sets.openedFromDevice 50 498

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M032

#print axioms Cert.M032.verified
