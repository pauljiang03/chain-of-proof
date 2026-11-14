import ChainOfProof
open ChainOfProof

namespace Cert.M219

def cited : List Fact := [
  ⟨377, .emailSent, 1427225642435000, 1000000, 216, 208⟩,
  ⟨395, .tag, 1794614400000000, 1, 216, 230⟩ ]

def claim : Claim := .both (Sets.emailed 377) (Sets.tagged 377 .obj 395 230)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M219

#print axioms Cert.M219.verified
