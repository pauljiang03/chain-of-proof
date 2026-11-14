import ChainOfProof
open ChainOfProof

namespace Cert.A231

def cited : List Fact := [
  ⟨199, .fileDeleted, 1427227902836000, 1, 114, 4⟩,
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.deletedAfter 199 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A231

#print axioms Cert.A231.verified
