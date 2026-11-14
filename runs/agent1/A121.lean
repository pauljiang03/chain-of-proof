import ChainOfProof
open ChainOfProof

namespace Cert.A121

def cited : List Fact := [
  ⟨31, .lnkTarget, 1427142413783793, 1, 25, 26⟩,
  ⟨214, .tag, 1794614400000000, 1, 25, 118⟩ ]

def claim : Claim := .both (Sets.opened 31) (Sets.tagged 31 .obj 214 118)

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A121

#print axioms Cert.A121.verified
