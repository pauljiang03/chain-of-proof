import ChainOfProof
open ChainOfProof

namespace Cert.A239

def cited : List Fact := [
  ⟨207, .fileDeleted, 1427227902851000, 1, 122, 4⟩,
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.deletedAfter 207 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A239

#print axioms Cert.A239.verified
