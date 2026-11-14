import ChainOfProof
open ChainOfProof

namespace Cert.M210

def cited : List Fact := [
  ⟨368, .emailSent, 1427131767000000, 1000000, 205, 206⟩ ]

def claim : Claim := Sets.emailed 368

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M210

#print axioms Cert.M210.verified
