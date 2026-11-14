import ChainOfProof
open ChainOfProof

namespace Cert.M218

def cited : List Fact := [
  ⟨376, .emailSent, 1427204110365000, 1000000, 215, 208⟩,
  ⟨394, .tag, 1794614400000000, 1, 215, 230⟩ ]

def claim : Claim := .both (Sets.emailed 376) (Sets.tagged 376 .obj 394 230)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M218

#print axioms Cert.M218.verified
