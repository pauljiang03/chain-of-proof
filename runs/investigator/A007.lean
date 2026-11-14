import ChainOfProof
open ChainOfProof

namespace Cert.A007

def cited : List Fact := [
  ⟨364, .volumeSeen, 1427135472853809, 1, 202, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.recordedOnDevice 364 374

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A007

#print axioms Cert.A007.verified
