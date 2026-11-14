import ChainOfProof
open ChainOfProof

namespace Cert.A276

def cited : List Fact := [
  ⟨303, .emailSent, 1427225642435000, 1000000, 182, 174⟩,
  ⟨305, .cdBurn, 1427226467407829, 1, 184, 185⟩ ]

def claim : Claim := .before 303 305

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A276

#print axioms Cert.A276.verified
