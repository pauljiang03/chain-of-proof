import ChainOfProof
open ChainOfProof

namespace Cert.A230

def cited : List Fact := [
  ⟨198, .fileDeleted, 1427226707149000, 1, 113, 4⟩,
  ⟨305, .cdBurn, 1427226467407829, 1, 184, 185⟩ ]

def claim : Claim := Sets.deletedAfter 198 305

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A230

#print axioms Cert.A230.verified
