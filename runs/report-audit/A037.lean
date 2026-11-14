import ChainOfProof
open ChainOfProof

namespace Cert.A037

def cited : List Fact := [
  ⟨40, .lnkTarget, 1427142457263674, 1, 28, 26⟩ ]

def claim : Claim := Sets.opened 40

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A037

#print axioms Cert.A037.verified
