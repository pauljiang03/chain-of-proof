import ChainOfProof
open ChainOfProof

namespace Cert.A274

def cited : List Fact := [
  ⟨109, .fileCreated, 1427205577630000, 10000, 93, 69⟩,
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩ ]

def claim : Claim := .before 109 41

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A274

#print axioms Cert.A274.verified
