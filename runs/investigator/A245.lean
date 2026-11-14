import ChainOfProof
open ChainOfProof

namespace Cert.A245

def cited : List Fact := [
  ⟨294, .emailSent, 1427131767000000, 1000000, 171, 172⟩ ]

def claim : Claim := Sets.emailed 294

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A245

#print axioms Cert.A245.verified
