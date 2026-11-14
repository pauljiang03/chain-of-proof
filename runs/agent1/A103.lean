import ChainOfProof
open ChainOfProof

namespace Cert.A103

def cited : List Fact := [
  ⟨24, .lnkTarget, 1427135874522916, 1, 20, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 24 241

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A103

#print axioms Cert.A103.verified
