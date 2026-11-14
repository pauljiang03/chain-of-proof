import ChainOfProof
open ChainOfProof

namespace Cert.A233

def cited : List Fact := [
  ⟨201, .fileDeleted, 1427227902851000, 1, 116, 4⟩,
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.deletedAfter 201 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A233

#print axioms Cert.A233.verified
