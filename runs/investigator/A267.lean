import ChainOfProof
open ChainOfProof

namespace Cert.A267

def cited : List Fact := [
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩ ]

def claim : Claim := .before 1 21

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A267

#print axioms Cert.A267.verified
