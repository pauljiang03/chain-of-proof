import ChainOfProof
open ChainOfProof

namespace Cert.A223

def cited : List Fact := [
  ⟨107, .fileCreated, 1427144137810000, 10000, 91, 69⟩,
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩ ]

def claim : Claim := .before 107 3

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A223

#print axioms Cert.A223.verified
