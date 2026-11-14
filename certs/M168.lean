import ChainOfProof
open ChainOfProof

namespace Cert.M168

def cited : List Fact := [
  ⟨302, .emailSent, 1427204110365000, 1000000, 181, 174⟩,
  ⟨320, .tag, 1794614400000000, 1, 181, 196⟩ ]

def claim : Claim := .both (Sets.emailed 302) (Sets.tagged 302 .obj 320 196)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M168

#print axioms Cert.M168.verified
