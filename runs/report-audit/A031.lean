import ChainOfProof
open ChainOfProof

namespace Cert.A031

def cited : List Fact := [
  ⟨30, .lnkTarget, 1427135903445366, 1, 22, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := Sets.openedFromDevice 30 374

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A031

#print axioms Cert.A031.verified
