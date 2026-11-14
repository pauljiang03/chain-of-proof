import ChainOfProof
open ChainOfProof

namespace Cert.A176

def cited : List Fact := [
  ⟨30, .lnkTarget, 1427135903445366, 1, 22, 19⟩,
  ⟨31, .lnkTarget, 1427142413783793, 1, 25, 26⟩ ]

def claim : Claim := .before 30 31

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A176

#print axioms Cert.A176.verified
