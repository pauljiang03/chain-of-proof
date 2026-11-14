import ChainOfProof
open ChainOfProof

namespace Cert.A149

def cited : List Fact := [
  ⟨31, .lnkTarget, 1427142413783793, 1, 25, 26⟩,
  ⟨338, .tag, 1794614400000000, 1, 25, 197⟩ ]

def claim : Claim := Sets.tagged 31 .obj 338 197

theorem verified : holds cited claim = true := by decide +kernel

end Cert.A149

#print axioms Cert.A149.verified
