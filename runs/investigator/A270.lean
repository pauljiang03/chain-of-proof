import ChainOfProof
open ChainOfProof

namespace Cert.A270

def cited : List Fact := [
  ⟨31, .lnkTarget, 1427142413783793, 1, 25, 26⟩,
  ⟨300, .emailSent, 1427143279000000, 1000000, 179, 172⟩ ]

def claim : Claim := .before 31 300

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A270

#print axioms Cert.A270.verified
