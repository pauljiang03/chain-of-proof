import ChainOfProof
open ChainOfProof

namespace Cert.A269

def cited : List Fact := [
  ⟨299, .emailSent, 1427138825282000, 1000000, 178, 174⟩,
  ⟨31, .lnkTarget, 1427142413783793, 1, 25, 26⟩ ]

def claim : Claim := .before 299 31

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A269

#print axioms Cert.A269.verified
