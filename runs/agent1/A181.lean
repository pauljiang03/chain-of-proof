import ChainOfProof
open ChainOfProof

namespace Cert.A181

def cited : List Fact := [
  ⟨164, .webSearch, 1427140564087328, 1, 99, 69⟩,
  ⟨84, .fileCreated, 1427140590661442, 1, 67, 4⟩ ]

def claim : Claim := .before 164 84

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A181

#print axioms Cert.A181.verified
