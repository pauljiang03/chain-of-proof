import ChainOfProof
open ChainOfProof

namespace Cert.M216

def cited : List Fact := [
  ⟨374, .emailSent, 1427143279000000, 1000000, 213, 206⟩,
  ⟨393, .tag, 1794614400000000, 1, 213, 230⟩ ]

def claim : Claim := .both (Sets.emailed 374) (Sets.tagged 374 .obj 393 230)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M216

#print axioms Cert.M216.verified
