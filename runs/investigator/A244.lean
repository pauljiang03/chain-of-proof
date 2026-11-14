import ChainOfProof
open ChainOfProof

namespace Cert.A244

def cited : List Fact := [
  ⟨300, .emailSent, 1427143279000000, 1000000, 179, 172⟩,
  ⟨319, .tag, 1794614400000000, 1, 179, 196⟩ ]

def claim : Claim := Sets.tagged 300 .obj 319 196

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A244

#print axioms Cert.A244.verified
