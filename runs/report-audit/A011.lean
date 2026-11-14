import ChainOfProof
open ChainOfProof

namespace Cert.A011

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨366, .volumeSeen, 1427205514439312, 1, 203, 31⟩ ]

def claim : Claim := .before 3 366

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A011

#print axioms Cert.A011.verified
