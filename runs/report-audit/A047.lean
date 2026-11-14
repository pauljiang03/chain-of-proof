import ChainOfProof
open ChainOfProof

namespace Cert.A047

def cited : List Fact := [
  ⟨53, .lnkTarget, 1427230874320463, 1, 43, 40⟩,
  ⟨370, .volumeSeen, 1427230870763657, 1, 204, 40⟩ ]

def claim : Claim := Sets.openedFromRecorded 53 370

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A047

#print axioms Cert.A047.verified
