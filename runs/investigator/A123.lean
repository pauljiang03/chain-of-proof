import ChainOfProof
open ChainOfProof

namespace Cert.A123

def cited : List Fact := [
  ⟨27, .lnkTarget, 1427135901214563, 1, 23, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 27 374

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A123

#print axioms Cert.A123.verified
