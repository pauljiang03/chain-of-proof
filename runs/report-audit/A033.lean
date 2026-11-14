import ChainOfProof
open ChainOfProof

namespace Cert.A033

def cited : List Fact := [
  ⟨33, .lnkTarget, 1427142413986593, 1, 25, 26⟩ ]

def claim : Claim := Sets.opened 33

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A033

#print axioms Cert.A033.verified
