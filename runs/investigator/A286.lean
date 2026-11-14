import ChainOfProof
open ChainOfProof

namespace Cert.A286

def cited : List Fact := [
  ⟨260, .webSearch, 1427140564087328, 1, 155, 125⟩,
  ⟨84, .fileCreated, 1427140590661442, 1, 67, 4⟩ ]

def claim : Claim := .before 260 84

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A286

#print axioms Cert.A286.verified
