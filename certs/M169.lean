import ChainOfProof
open ChainOfProof

namespace Cert.M169

def cited : List Fact := [
  ⟨303, .emailSent, 1427225642435000, 1000000, 182, 174⟩,
  ⟨321, .tag, 1794614400000000, 1, 182, 196⟩ ]

def claim : Claim := .both (Sets.emailed 303) (Sets.tagged 303 .obj 321 196)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M169

#print axioms Cert.M169.verified
