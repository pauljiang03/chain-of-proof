import ChainOfProof
open ChainOfProof

namespace Cert.A127

def cited : List Fact := [
  ⟨21, .lnkTarget, 1427135840499256, 1, 18, 19⟩,
  ⟨365, .volumeSeen, 1427135840499256, 1, 202, 19⟩,
  ⟨374, .volumeOnDevice, 1794614400000000, 1, 1, 19⟩ ]

def claim : Claim := .both (Sets.openedFromRecorded 21 365) (Sets.recordedOnDevice 365 374)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A127

#print axioms Cert.A127.verified
