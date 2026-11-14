import ChainOfProof
open ChainOfProof

namespace Cert.M220

def cited : List Fact := [
  ⟨378, .emailSent, 1427231109679000, 1000000, 217, 208⟩,
  ⟨391, .tag, 1794614400000000, 1, 217, 230⟩ ]

def claim : Claim := .both (Sets.emailed 378) (Sets.tagged 378 .obj 391 230)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M220

#print axioms Cert.M220.verified
