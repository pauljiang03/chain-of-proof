import ChainOfProof
open ChainOfProof

namespace Cert.M034

def cited : List Fact := [
  ⟨52, .lnkTarget, 1427230872900860, 1, 42, 40⟩,
  ⟨370, .volumeSeen, 1427230870763657, 1, 204, 40⟩ ]

def claim : Claim := Sets.openedFromRecorded 52 370

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M034

#print axioms Cert.M034.verified
