import ChainOfProof
open ChainOfProof

namespace Cert.A234

def cited : List Fact := [
  ⟨202, .fileDeleted, 1427227902851000, 1, 117, 4⟩,
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.deletedAfter 202 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A234

#print axioms Cert.A234.verified
