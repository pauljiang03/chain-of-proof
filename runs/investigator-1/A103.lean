import ChainOfProof
open ChainOfProof

namespace Cert.A103

def cited : List Fact := [
  ⟨9452, .fileRenamed, 1427226396084504, 1, 13107, 13108⟩,
  ⟨380, .cdBurn, 1427226467657431, 1, 220, 221⟩ ]

def claim : Claim := .before 9452 380

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A103

#print axioms Cert.A103.verified
