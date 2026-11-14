import ChainOfProof
open ChainOfProof

namespace Cert.A078

def cited : List Fact := [
  ⟨304, .emailSent, 1427231109679000, 1000000, 183, 174⟩,
  ⟨317, .tag, 1794614400000000, 1, 183, 196⟩ ]

def claim : Claim := .both (Sets.emailed 304) (Sets.tagged 304 .obj 317 196)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A078

#print axioms Cert.A078.verified
