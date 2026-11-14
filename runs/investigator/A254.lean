import ChainOfProof
open ChainOfProof

namespace Cert.A254

def cited : List Fact := [
  ⟨303, .emailSent, 1427225642435000, 1000000, 182, 174⟩ ]

def claim : Claim := Sets.emailed 303

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A254

#print axioms Cert.A254.verified
