import ChainOfProof
open ChainOfProof

namespace Cert.A055

def cited : List Fact := [
  ⟨31, .lnkTarget, 1427142413783793, 1, 25, 26⟩,
  ⟨412, .tag, 1794614400000000, 1, 25, 231⟩,
  ⟨36, .lnkTarget, 1427142453267067, 1, 28, 26⟩,
  ⟨410, .tag, 1794614400000000, 1, 28, 231⟩ ]

def claim : Claim := .both (Sets.opened 31) (.both (Sets.tagged 31 .obj 412 231) (.both (Sets.opened 36) (Sets.tagged 36 .obj 410 231)))

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A055

#print axioms Cert.A055.verified
