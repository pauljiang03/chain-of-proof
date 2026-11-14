import ChainOfProof
open ChainOfProof

namespace Cert.M030

def cited : List Fact := [
  ⟨48, .lnkTarget, 1427229858901833, 1, 34, 35⟩ ]

def claim : Claim := Sets.opened 48

theorem verified : holds cited claim = true := by decide +kernel

end Cert.M030

#print axioms Cert.M030.verified
