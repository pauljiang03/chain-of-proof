import ChainOfProof
open ChainOfProof

namespace Cert.A266

def cited : List Fact := [
  ⟨228, .webSearch, 1427133987545120, 1, 134, 125⟩,
  ⟨1, .usbInsert, 1427135470593000, 1000, 1, 0⟩ ]

def claim : Claim := .before 228 1

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A266

#print axioms Cert.A266.verified
