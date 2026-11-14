import ChainOfProof
open ChainOfProof

namespace Cert.A096

def cited : List Fact := [
  ⟨372, .emailSent, 1427138782000000, 1000000, 211, 206⟩,
  ⟨31, .lnkTarget, 1427142413783793, 1, 25, 26⟩ ]

def claim : Claim := .before 372 31

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A096

#print axioms Cert.A096.verified
