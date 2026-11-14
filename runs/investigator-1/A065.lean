import ChainOfProof
open ChainOfProof

namespace Cert.A065

def cited : List Fact := [
  ⟨3, .usbInsert, 1427205512859000, 1000, 2, 0⟩,
  ⟨109, .fileCreated, 1427205577630000, 10000, 93, 69⟩ ]

def claim : Claim := .before 3 109

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A065

#print axioms Cert.A065.verified
