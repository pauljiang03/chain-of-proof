import ChainOfProof
open ChainOfProof

namespace Cert.A236

def cited : List Fact := [
  ⟨204, .fileDeleted, 1427227902851000, 1, 119, 4⟩,
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.deletedAfter 204 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A236

#print axioms Cert.A236.verified
