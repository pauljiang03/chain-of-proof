import ChainOfProof
open ChainOfProof

namespace Cert.A228

def cited : List Fact := [
  ⟨196, .fileDeleted, 1427226707133000, 1, 111, 4⟩,
  ⟨305, .cdBurn, 1427226467407829, 1, 184, 185⟩ ]

def claim : Claim := Sets.deletedAfter 196 305

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A228

#print axioms Cert.A228.verified
