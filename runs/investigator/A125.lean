import ChainOfProof
open ChainOfProof

namespace Cert.A125

def cited : List Fact := [
  ⟨29, .lnkTarget, 1427135903414167, 1, 24, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 29 374

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A125

#print axioms Cert.A125.verified
