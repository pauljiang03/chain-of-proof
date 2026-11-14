import ChainOfProof
open ChainOfProof

namespace Cert.A014

def cited : List Fact := [
  ⟨492, .volumeSeen, 1427230870763657, 1, 252, 40⟩,
  ⟨498, .volumeOnDevice, 1794614400000000, 1, 249, 40⟩ ]

def claim : Claim := Sets.recordedOnDevice 492 498

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A014

#print axioms Cert.A014.verified
