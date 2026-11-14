import ChainOfProof
open ChainOfProof

namespace Cert.A055

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨108, .fileCreated, 1427205567120000, 10000, 92, 69⟩ ]

def claim : Claim := .before 3 108

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A055

#print axioms Cert.A055.verified
