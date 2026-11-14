import ChainOfProof
open ChainOfProof

namespace Cert.A014

def cited : List Fact := [
  ⟨371, .volumeSeen, 1427230954309607, 1, 203, 205⟩,
  ⟨375, .volumeOnDevice, 1794614400000000, 1, 2, 205⟩ ]

def claim : Claim := Sets.recordedOnDevice 371 375

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A014

#print axioms Cert.A014.verified
