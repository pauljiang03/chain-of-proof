import ChainOfProof
open ChainOfProof

namespace Cert.A129

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩ ]

def claim : Claim := .before 3 41

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A129

#print axioms Cert.A129.verified
