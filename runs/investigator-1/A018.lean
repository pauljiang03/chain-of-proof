import ChainOfProof
open ChainOfProof

namespace Cert.A018

def cited : List Fact := [
  ⟨498, .volumeOnDevice, 1794614400000000, 1, 249, 40⟩,
  ⟨473, .tag, 1794614400000000, 1, 249, 228⟩ ]

def claim : Claim := Sets.tagged 498 .obj 473 228

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A018

#print axioms Cert.A018.verified
