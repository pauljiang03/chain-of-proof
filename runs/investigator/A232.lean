import ChainOfProof
open ChainOfProof

namespace Cert.A232

def cited : List Fact := [
  ⟨200, .fileDeleted, 1427227902836000, 1, 115, 4⟩,
  ⟨308, .cdBurn, 1427226971965935, 1, 186, 187⟩ ]

def claim : Claim := Sets.deletedAfter 200 308

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A232

#print axioms Cert.A232.verified
