import ChainOfProof
open ChainOfProof

namespace Cert.A160

def cited : List Fact := [
  ⟨51, .lnkTarget, 1427230870904057, 1, 41, 40⟩,
  ⟨370, .volumeSeen, 1427230870763657, 1, 204, 40⟩ ]

def claim : Claim := Sets.openedFromRecorded 51 370

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A160

#print axioms Cert.A160.verified
