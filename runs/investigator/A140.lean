import ChainOfProof
open ChainOfProof

namespace Cert.A140

def cited : List Fact := [
  ⟨32, .lnkTarget, 1427142413924193, 1, 27, 26⟩ ]

def claim : Claim := Sets.opened 32

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A140

#print axioms Cert.A140.verified
