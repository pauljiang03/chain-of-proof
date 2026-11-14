import ChainOfProof
open ChainOfProof

namespace Cert.A102

def cited : List Fact := [
  ⟨377, .emailSent, 1427225642435000, 1000000, 216, 208⟩,
  ⟨380, .cdBurn, 1427226467657431, 1, 220, 221⟩ ]

def claim : Claim := .before 377 380

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A102

#print axioms Cert.A102.verified
