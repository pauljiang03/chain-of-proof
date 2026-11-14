import ChainOfProof
open ChainOfProof

namespace Cert.A237

def cited : List Fact := [
  ⟨205, .fileDeleted, 1427227902851000, 1, 120, 4⟩,
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.deletedAfter 205 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A237

#print axioms Cert.A237.verified
