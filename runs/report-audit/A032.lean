import ChainOfProof
open ChainOfProof

namespace Cert.A032

def cited : List Fact := [
  ⟨31, .lnkTarget, 1427142413783793, 1, 25, 26⟩ ]

def claim : Claim := Sets.opened 31

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A032

#print axioms Cert.A032.verified
