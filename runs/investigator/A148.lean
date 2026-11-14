import ChainOfProof
open ChainOfProof

namespace Cert.A148

def cited : List Fact := [
  ⟨40, .lnkTarget, 1427142457263674, 1, 28, 26⟩ ]

def claim : Claim := Sets.opened 40

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A148

#print axioms Cert.A148.verified
