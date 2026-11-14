import ChainOfProof
open ChainOfProof

namespace Cert.A015

def cited : List Fact := [
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩ ]

def claim : Claim := .before 1 3

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A015

#print axioms Cert.A015.verified
