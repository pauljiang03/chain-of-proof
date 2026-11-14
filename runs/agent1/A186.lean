import ChainOfProof
open ChainOfProof

namespace Cert.A186

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨44, .lnkTarget, 1427229853752619, 1, 34, 35⟩ ]

def claim : Claim := .before 41 44

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A186

#print axioms Cert.A186.verified
