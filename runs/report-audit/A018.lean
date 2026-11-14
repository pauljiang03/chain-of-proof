import ChainOfProof
open ChainOfProof

namespace Cert.A018

def cited : List Fact := [
  ⟨50, .lnkTarget, 1427230870763657, 1, 23, 40⟩,
  ⟨370, .volumeSeen, 1427230870763657, 1, 204, 40⟩ ]

def claim : Claim := Sets.openedFromRecorded 50 370

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A018

#print axioms Cert.A018.verified
