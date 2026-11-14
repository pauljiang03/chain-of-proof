import ChainOfProof
open ChainOfProof

namespace Cert.A229

def cited : List Fact := [
  ⟨197, .fileDeleted, 1427226707133000, 1, 112, 4⟩,
  ⟨305, .cdBurn, 1427226467407829, 1, 184, 185⟩ ]

def claim : Claim := Sets.deletedAfter 197 305

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A229

#print axioms Cert.A229.verified
