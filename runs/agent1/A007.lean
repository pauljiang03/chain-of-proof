import ChainOfProof
open ChainOfProof

namespace Cert.A007

def cited : List Fact := [
  ⟨236, .volumeSeen, 1427135472853809, 1, 119, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.recordedOnDevice 236 241

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A007

#print axioms Cert.A007.verified
