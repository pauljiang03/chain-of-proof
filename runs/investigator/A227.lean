import ChainOfProof
open ChainOfProof

namespace Cert.A227

def cited : List Fact := [
  ⟨195, .fileDeleted, 1427226707117000, 1, 110, 4⟩,
  ⟨305, .cdBurn, 1427226467407829, 1, 184, 185⟩ ]

def claim : Claim := Sets.deletedAfter 195 305

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A227

#print axioms Cert.A227.verified
