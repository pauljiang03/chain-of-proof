import ChainOfProof
open ChainOfProof

namespace Cert.A279

def cited : List Fact := [
  ⟨41, .lnkTarget, 1427205683393024, 1, 30, 31⟩,
  ⟨371, .volumeSeen, 1427230954309607, 1, 203, 205⟩ ]

def claim : Claim := .before 41 371

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A279

#print axioms Cert.A279.verified
