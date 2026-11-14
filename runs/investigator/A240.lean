import ChainOfProof
open ChainOfProof

namespace Cert.A240

def cited : List Fact := [
  ⟨208, .fileDeleted, 1427227902851000, 1, 123, 4⟩,
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.deletedAfter 208 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A240

#print axioms Cert.A240.verified
