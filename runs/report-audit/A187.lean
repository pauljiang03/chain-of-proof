import ChainOfProof
open ChainOfProof

namespace Cert.A187

def cited : List Fact := [
  ⟨304, .emailSent, 1427231109679000, 1000000, 183, 174⟩ ]

def claim : Claim := Sets.emailed 304

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A187

#print axioms Cert.A187.verified
