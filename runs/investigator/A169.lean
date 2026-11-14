import ChainOfProof
open ChainOfProof

namespace Cert.A169

def cited : List Fact := [
  ⟨125, .fileCreated, 1427222920734358, 1, 44, 4⟩,
  ⟨192, .fileModified, 1427223570611170, 1, 44, 4⟩ ]

def claim : Claim := .before 125 192

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A169

#print axioms Cert.A169.verified
