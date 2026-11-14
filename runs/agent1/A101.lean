import ChainOfProof
open ChainOfProof

namespace Cert.A101

def cited : List Fact := [
  ⟨22, .lnkTarget, 1427135874491716, 1, 18, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 22 241

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A101

#print axioms Cert.A101.verified
