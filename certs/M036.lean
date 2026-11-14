import ChainOfProof
open ChainOfProof

namespace Cert.M036

def cited : List Fact := [
  ⟨54, .lnkTarget, 1427230874336063, 1, 23, 40⟩,
  ⟨370, .volumeSeen, 1427230870763657, 1, 204, 40⟩ ]

def claim : Claim := Sets.openedFromRecorded 54 370

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M036

#print axioms Cert.M036.verified
