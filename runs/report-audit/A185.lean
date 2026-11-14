import ChainOfProof
open ChainOfProof

namespace Cert.A185

def cited : List Fact := [
  ⟨302, .emailSent, 1427204110365000, 1000000, 181, 174⟩,
  ⟨320, .tag, 1794614400000000, 1, 181, 196⟩ ]

def claim : Claim := Sets.tagged 302 .obj 320 196

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A185

#print axioms Cert.A185.verified
