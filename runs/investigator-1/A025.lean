import ChainOfProof
open ChainOfProof

namespace Cert.A025

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨488, .volumeSeen, 1427205514439312, 1, 251, 31⟩ ]

def claim : Claim := .before 3 488

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A025

#print axioms Cert.A025.verified
