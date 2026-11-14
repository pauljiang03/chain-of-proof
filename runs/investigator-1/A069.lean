import ChainOfProof
open ChainOfProof

namespace Cert.A069

def cited : List Fact := [
  ⟨269, .fileDeleted, 1427226707117000, 1, 144, 4⟩,
  ⟨9453, .fileRenamed, 1427226398814509, 1, 13109, 13110⟩ ]

def claim : Claim := Sets.deletedAfter 269 9453

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A069

#print axioms Cert.A069.verified
