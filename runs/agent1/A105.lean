import ChainOfProof
open ChainOfProof

namespace Cert.A105

def cited : List Fact := [
  ⟨27, .lnkTarget, 1427135901214563, 1, 23, 19⟩,
  ⟨241, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 27 241

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A105

#print axioms Cert.A105.verified
