import ChainOfProof
open ChainOfProof

namespace Cert.A076

def cited : List Fact := [
  ⟨301, .emailSent, 1427203557000000, 1000000, 180, 172⟩,
  ⟨302, .emailSent, 1427204110365000, 1000000, 181, 174⟩,
  ⟨320, .tag, 1794614400000000, 1, 181, 196⟩ ]

def claim : Claim := .both (Sets.emailed 301) (.both (Sets.emailed 302) (Sets.tagged 302 .obj 320 196))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A076

#print axioms Cert.A076.verified
