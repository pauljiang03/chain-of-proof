import ChainOfProof
open ChainOfProof

namespace Cert.A008

def cited : List Fact := [
  ⟨238, .volumeSeen, 1427230954309607, 1, 120, 121⟩,
  ⟨242, .volumeOnDevice, 1794614400000000, 1, 2, 121⟩ ]

def claim : Claim := Sets.recordedOnDevice 238 242

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A008

#print axioms Cert.A008.verified
