import ChainOfProof
open ChainOfProof

namespace Cert.A119

def cited : List Fact := [
  ⟨22, .lnkTarget, 1427135874491716, 1, 18, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 22 374

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A119

#print axioms Cert.A119.verified
