import ChainOfProof
open ChainOfProof

namespace Cert.M028

def cited : List Fact := [
  ⟨46, .lnkTarget, 1427229856507227, 1, 37, 0⟩ ]

def claim : Claim := Sets.opened 46

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M028

#print axioms Cert.M028.verified
