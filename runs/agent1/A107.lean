import ChainOfProof
open ChainOfProof

namespace Cert.A107

def cited : List Fact := [
  ⟨29, .lnkTarget, 1427135903414167, 1, 24, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 29 241

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A107

#print axioms Cert.A107.verified
