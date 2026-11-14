import ChainOfProof
open ChainOfProof

namespace Cert.A052

def cited : List Fact := [
  ⟨192, .fileModified, 1427223570611170, 1, 44, 4⟩,
  ⟨55, .lnkTarget, 1427297289748404, 1, 44, 4⟩ ]

def claim : Claim := .before 192 55

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A052

#print axioms Cert.A052.verified
