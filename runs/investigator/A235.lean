import ChainOfProof
open ChainOfProof

namespace Cert.A235

def cited : List Fact := [
  ⟨203, .fileDeleted, 1427227902851000, 1, 118, 4⟩,
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.deletedAfter 203 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A235

#print axioms Cert.A235.verified
