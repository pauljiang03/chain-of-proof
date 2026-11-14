import ChainOfProof
open ChainOfProof

namespace Cert.A281

def cited : List Fact := [
  ⟨304, .emailSent, 1427231109679000, 1000000, 183, 174⟩,
  ⟨289, .webSearch, 1427231210726427, 1, 167, 125⟩ ]

def claim : Claim := .before 304 289

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A281

#print axioms Cert.A281.verified
