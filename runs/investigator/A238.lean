import ChainOfProof
open ChainOfProof

namespace Cert.A238

def cited : List Fact := [
  ⟨206, .fileDeleted, 1427227902851000, 1, 121, 4⟩,
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.deletedAfter 206 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A238

#print axioms Cert.A238.verified
