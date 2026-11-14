import ChainOfProof
open ChainOfProof

namespace Cert.A173

def cited : List Fact := [
  ⟨132, .webSearch, 1427133987545120, 1, 78, 69⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩ ]

def claim : Claim := .before 132 1

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A173

#print axioms Cert.A173.verified
