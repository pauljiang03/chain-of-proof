import ChainOfProof
open ChainOfProof

namespace Cert.A071

def cited : List Fact := [
  ⟨85, .fileCreated, 1427144117150000, 10000, 68, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩ ]

def claim : Claim := .before 85 3

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A071

#print axioms Cert.A071.verified
